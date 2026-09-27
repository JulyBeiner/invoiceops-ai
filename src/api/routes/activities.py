import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import extract

from api.extensions import db
from api.models import Activity, BillingRun, Client, Service
from api.routes.helpers import current_tenant_id

activities_bp = Blueprint("activities", __name__)


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
        performed_on = date.fromisoformat(str(data.get("performed_on")))
    except ValueError:
        return None, "performed_on must be a date (YYYY-MM-DD)"
    if db.session.scalar(db.select(BillingRun).filter_by(
            tenant_id=tenant_id, year=performed_on.year,
            month=performed_on.month)):
        return None, f"{performed_on:%Y-%m} is already closed"
    try:
        quantity = Decimal(str(data.get("quantity"))).quantize(Decimal("0.01"))
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


def _read_csv_rows(file_storage):
    """Decode the uploaded CSV. Return (rows, None) or (None, error)."""
    try:
        text = file_storage.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "file must be UTF-8 text"
    reader = csv.DictReader(io.StringIO(text))
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

    clients = {c.name.lower(): c.id for c in db.session.scalars(
        db.select(Client).filter_by(tenant_id=tenant_id, is_archived=False))}
    services = {s.name.lower(): s.id for s in db.session.scalars(
        db.select(Service).filter_by(tenant_id=tenant_id))}
    existing_ids = set(db.session.scalars(db.select(Activity.external_id).where(
        Activity.tenant_id == tenant_id, Activity.external_id.is_not(None))))

    preview, to_save, seen = [], [], set()
    for line, row in enumerate(rows, start=2):
        external_id = (row.get("external_id") or "").strip()
        if external_id and (external_id in existing_ids or external_id in seen):
            preview.append({"line": line, "status": "duplicate", "data": row})
            continue
        data = {
            "client_id": clients.get((row.get("client") or "").strip().lower()),
            "service_id": services.get((row.get("service") or "").strip().lower()),
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
        preview.append({"line": line, "status": "ok", "data": row})

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
