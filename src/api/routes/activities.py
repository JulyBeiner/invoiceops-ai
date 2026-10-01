import csv
import io
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from difflib import get_close_matches

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import extract

from api.extensions import db
from api.models import Activity, BillingRun, Client, Service
from api.routes.helpers import current_tenant_id
from api.services import ai

activities_bp = Blueprint("activities", __name__)


def _parse_date(value):
    """Accept ISO (2026-09-10) and Spanish (10/09/2026) dates."""
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text, "%d/%m/%Y").date()


def _parse_quantity(value):
    """Accept a Spanish decimal comma: '3,5' -> Decimal('3.50')."""
    text = str(value if value is not None else "").strip().replace(",", ".")
    return Decimal(text).quantize(Decimal("0.01"))


def _parse_activity(data, tenant_id):
    """Validate one activity's data. Return (Activity, None) or (None, error)."""
    client = db.session.scalar(db.select(Client).filter_by(
        id=data.get("client_id"), tenant_id=tenant_id))
    if client is None:
        return None, "client not found"
    service = db.session.scalar(db.select(Service).filter_by(
        id=data.get("service_id"), tenant_id=tenant_id))
    if service is None:
        return None, "service not found"
    try:
        performed_on = _parse_date(data.get("performed_on"))
    except ValueError:
        return None, "performed_on must be a date (YYYY-MM-DD or DD/MM/YYYY)"
    if db.session.scalar(db.select(BillingRun).filter_by(
            tenant_id=tenant_id, year=performed_on.year,
            month=performed_on.month)):
        return None, f"{performed_on:%Y-%m} is already closed"
    try:
        quantity = _parse_quantity(data.get("quantity"))
    except InvalidOperation:
        return None, "quantity must be a number"
    if quantity <= 0:
        return None, "quantity must be greater than 0"
    external_id = str(data.get("external_id") or "").strip() or None

    activity = Activity(
        tenant_id=tenant_id, client_id=client.id, service_id=service.id,
        performed_on=performed_on, quantity=quantity, external_id=external_id,
    )
    return activity, None


@activities_bp.route("", methods=["POST"])
@jwt_required()
def create_activity():
    tenant_id = current_tenant_id()
    data = request.get_json(silent=True) or {}
    activity, error = _parse_activity(data, tenant_id)
    if error:
        return jsonify({"message": error}), 400
    if activity.external_id and db.session.scalar(db.select(Activity).filter_by(
            tenant_id=tenant_id, external_id=activity.external_id)):
        return jsonify({"message": "external_id already exists"}), 409

    db.session.add(activity)
    db.session.commit()
    return jsonify(activity.serialize()), 201


@activities_bp.route("", methods=["GET"])
@jwt_required()
def list_activities():
    query = db.select(Activity).filter_by(tenant_id=current_tenant_id())

    month = request.args.get("month")
    if month:
        try:
            year, month_number = (int(part) for part in month.split("-"))
        except ValueError:
            return jsonify({"message": "month must be YYYY-MM"}), 400
        query = query.filter(
            extract("year", Activity.performed_on) == year,
            extract("month", Activity.performed_on) == month_number,
        )
    client_id = request.args.get("client_id", type=int)
    if client_id:
        query = query.filter_by(client_id=client_id)

    activities = db.session.scalars(
        query.order_by(Activity.performed_on, Activity.id)).all()
    return jsonify([activity.serialize() for activity in activities]), 200


CSV_COLUMNS = ("external_id", "client", "service", "performed_on", "quantity")
STOPWORDS = {"de", "del", "la", "el", "los", "las", "y", "sl", "sa", "slu"}


def _normalize(text):
    """'Limpieza de Oficinas S.L.' -> 'limpieza oficinas' (no accents, case, filler)."""
    ascii_text = unicodedata.normalize("NFKD", text or "").encode(
        "ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_text.lower())
    return " ".join(word for word in words if word not in STOPWORDS)


def _catalog(items):
    """{normalized name: item} for clients or services."""
    return {_normalize(item.name): item for item in items}


def _match(name, catalog):
    """Find the item whose name means the same: exact after normalizing,
    else the single close match (typos); None if nothing or ambiguous."""
    key = _normalize(name)
    if not key:
        return None
    if key in catalog:
        return catalog[key]
    close = get_close_matches(key, list(catalog), n=2, cutoff=0.8)
    return catalog[close[0]] if len(close) == 1 else None


def _read_csv_rows(file_storage):
    """Decode the uploaded CSV. Return (rows, None) or (None, error)."""
    try:
        text = file_storage.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "file must be UTF-8 text"
    # Spanish Excel saves CSV with ";" — accept both separators.
    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fieldnames = [name.strip() for name in (reader.fieldnames or [])]
    missing = [name for name in CSV_COLUMNS if name not in fieldnames]
    if missing:
        return None, f"CSV is missing columns: {', '.join(missing)}"
    return list(reader), None


@activities_bp.route("/import", methods=["POST"])
@jwt_required()
def import_activities():
    tenant_id = current_tenant_id()
    file = request.files.get("file")
    if file is None:
        return jsonify({"message": "file is required"}), 400
    rows, error = _read_csv_rows(file)
    if error:
        return jsonify({"message": error}), 400

    clients = _catalog(db.session.scalars(
        db.select(Client).filter_by(tenant_id=tenant_id, is_archived=False)))
    services = _catalog(db.session.scalars(
        db.select(Service).filter_by(tenant_id=tenant_id)))
    existing_ids = set(db.session.scalars(db.select(Activity.external_id).where(
        Activity.tenant_id == tenant_id, Activity.external_id.is_not(None))))

    preview, to_save, seen = [], [], set()
    for line, row in enumerate(rows, start=2):
        external_id = (row.get("external_id") or "").strip()
        if external_id and (external_id in existing_ids or external_id in seen):
            preview.append({"line": line, "status": "duplicate", "data": row})
            continue
        matched_client = _match(row.get("client"), clients)
        matched_service = _match(row.get("service"), services)
        data = {
            "client_id": matched_client.id if matched_client else None,
            "service_id": matched_service.id if matched_service else None,
            "performed_on": (row.get("performed_on") or "").strip(),
            "quantity": (row.get("quantity") or "").strip(),
            "external_id": external_id,
        }
        activity, error = _parse_activity(data, tenant_id)
        if error:
            preview.append({"line": line, "status": "error",
                           "message": error, "data": row})
            continue
        if external_id:
            seen.add(external_id)
        to_save.append(activity)
        preview.append({"line": line, "status": "ok", "data": row,
                        "resolved": {"client": matched_client.name,
                                     "service": matched_service.name}})

    commit = request.args.get("commit") == "true"
    if commit:
        db.session.add_all(to_save)
        db.session.commit()

    summary = {
        "ok": len(to_save),
        "errors": sum(1 for r in preview if r["status"] == "error"),
        "duplicates": sum(1 for r in preview if r["status"] == "duplicate"),
    }
    return jsonify({"committed": commit, "summary": summary, "rows": preview}), 200


# --- AI capture: the AI reads and proposes; the person confirms ----------

SUGGEST_SYSTEM = (
    "Eres el asistente de InvoiceOps, una aplicación de facturación para "
    "empresas de limpieza y mantenimiento en España. Lees mensajes de "
    "trabajadores (WhatsApp, partes de trabajo, notas) y extraes las "
    "actividades realizadas: para qué cliente, qué servicio, qué día y qué "
    "cantidad (horas, unidades, servicios). Nunca inventes datos: si algo no "
    "está en el texto, déjalo vacío. Nunca calcules precios ni importes. "
    "Responde SOLO con JSON válido, sin texto antes ni después."
)

WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes",
               "sábado", "domingo")


def _recent_days(today):
    """'- hoy: miércoles 30/09/2026' ... for the last 7 days, so the model
    looks dates up instead of calculating them."""
    lines = []
    for offset in range(7):
        day = today - timedelta(days=offset)
        label = {0: "hoy", 1: "ayer"}.get(offset, "")
        lines.append(f"- {label + ': ' if label else ''}"
                     f"{WEEKDAYS_ES[day.weekday()]} {day:%d/%m/%Y}")
    return "\n".join(lines)


def _suggest_prompt(text, clients, services, today):
    """Build the user prompt: recent dates, the tenant's names and the schema."""
    client_names = "\n".join(f"- {c.name}" for c in clients) or "- (ninguno)"
    service_names = "\n".join(
        f"- {s.name} (unidad: {s.unit})" for s in services) or "- (ninguno)"
    return (
        "Fechas de los últimos días (usa esta lista, no calcules):\n"
        f"{_recent_days(today)}\n"
        "Si el texto no dice el día, usa hoy.\n\n"
        f"Clientes de la empresa (usa estos nombres exactos si coinciden):\n"
        f"{client_names}\n\n"
        f"Servicios de la empresa (usa estos nombres exactos si coinciden):\n"
        f"{service_names}\n\n"
        "Devuelve un objeto JSON con esta forma exacta:\n"
        '{"suggestions": [{"client": "nombre del cliente", '
        '"service": "nombre del servicio", "performed_on": "DD/MM/YYYY", '
        '"quantity": "número (horas o unidades)", "external_id": "referencia '
        'si aparece, si no vacío", "note": "texto original resumido", '
        '"confidence": "high | medium | low"}]}\n'
        "Una sugerencia por actividad. Si un mensaje no describe trabajo "
        "realizado, ignóralo.\n\n"
        f"Texto a analizar:\n\"\"\"\n{text}\n\"\"\""
    )


def _clean_suggestion(item, clients, services):
    """Re-check what the AI said: match names ourselves, parse date and
    quantity with the same rules as the CSV import, never trust blindly."""
    matched_client = _match(str(item.get("client") or ""), clients)
    matched_service = _match(str(item.get("service") or ""), services)
    try:
        performed_on = _parse_date(item.get("performed_on")).isoformat()
    except ValueError:
        performed_on = None
    try:
        quantity = _parse_quantity(item.get("quantity"))
        quantity = str(quantity) if quantity > 0 else None
    except InvalidOperation:
        quantity = None
    confidence = str(item.get("confidence") or "").lower()
    complete = all([matched_client, matched_service, performed_on, quantity])
    if confidence not in ("high", "medium", "low") or not complete:
        confidence = "low"
    return {
        "client": str(item.get("client") or "").strip(),
        "service": str(item.get("service") or "").strip(),
        "performed_on": performed_on,
        "quantity": quantity,
        "external_id": str(item.get("external_id") or "").strip(),
        "note": str(item.get("note") or "").strip(),
        "confidence": confidence,
        "resolved": {
            "client_id": matched_client.id if matched_client else None,
            "service_id": matched_service.id if matched_service else None,
        },
    }


IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@activities_bp.route("/suggest", methods=["POST"])
@jwt_required()
def suggest_activities():
    """Turn free text, a photo or a voice note into activity suggestions.

    JSON {"text": ...} or multipart with "text" and/or "file" (an image of a
    work sheet or chat, or an audio note). Writes nothing.
    """
    if not ai.is_configured():
        return jsonify({"message": "AI is not configured"}), 503
    tenant_id = current_tenant_id()
    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or request.form.get("text") or "").strip()

    images, transcript = [], None
    upload = request.files.get("file")
    if upload is not None and upload.filename:
        content = upload.read()
        if len(content) > MAX_UPLOAD_BYTES:
            return jsonify({"message": "file is too large (max 10 MB)"}), 400
        mime_type = (upload.mimetype or "").lower()
        if mime_type in IMAGE_TYPES:
            images = [(content, mime_type)]
        elif mime_type.startswith("audio/"):
            try:
                transcript = ai.transcribe(content, upload.filename, mime_type)
            except ai.AIError as error:
                return jsonify({"message": f"AI provider error: {error}"}), 502
            text = f"{text}\n{transcript}".strip()
        else:
            return jsonify({"message": "file must be an image (png, jpg, webp) "
                                       "or an audio note"}), 400
    if not text and not images:
        return jsonify({"message": "text is required"}), 400
    if images:
        text = (text or "(sin texto)") + (
            "\n\nAdemás hay una imagen adjunta (parte de trabajo, captura de "
            "chat o nota manuscrita): lee las actividades que aparezcan en ella.")

    clients = list(db.session.scalars(db.select(Client).filter_by(
        tenant_id=tenant_id, is_archived=False).order_by(Client.name)))
    services = list(db.session.scalars(db.select(Service).filter_by(
        tenant_id=tenant_id).order_by(Service.name)))
    prompt = _suggest_prompt(text, clients, services, date.today())
    try:
        answer = ai.complete(prompt, system=SUGGEST_SYSTEM, images=images)
    except ai.AIError as error:
        return jsonify({"message": f"AI provider error: {error}"}), 502

    raw = answer.get("suggestions") if isinstance(answer, dict) else None
    client_catalog, service_catalog = _catalog(clients), _catalog(services)
    suggestions = [_clean_suggestion(item, client_catalog, service_catalog)
                   for item in (raw or []) if isinstance(item, dict)]
    return jsonify({"suggestions": suggestions, "transcript": transcript}), 200