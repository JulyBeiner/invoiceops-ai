from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from api.extensions import db
from api.models import Client, Contract, ContractPrice, Service
from api.routes.activities import (IMAGE_TYPES, MAX_UPLOAD_BYTES, _catalog,
                                   _match, _normalize, _parse_quantity)
from api.routes.helpers import current_tenant_id
from api.routes.services import CATALOG
from api.services import ai

clients_bp = Blueprint("clients", __name__)


@clients_bp.route("", methods=["GET"])
@jwt_required()
def list_clients():
    tenant_id = current_tenant_id()
    clients = db.session.scalars(
        db.select(Client).filter_by(tenant_id=tenant_id).order_by(Client.name)
    ).all()
    return jsonify([client.serialize() for client in clients]), 200


@clients_bp.route("", methods=["POST"])
@jwt_required()
def create_client():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "name is required"}), 400

    client = Client(
        tenant_id=current_tenant_id(),
        name=name,
        tax_id=(data.get("tax_id") or "").strip() or None,
        email=(data.get("email") or "").strip().lower() or None,
    )
    db.session.add(client)
    db.session.commit()
    return jsonify(client.serialize()), 201


def _get_client(client_id):
    """Return the client if it belongs to the current tenant, else None."""
    return db.session.scalar(
        db.select(Client).filter_by(
            id=client_id, tenant_id=current_tenant_id())
    )


@clients_bp.route("/<int:client_id>", methods=["GET"])
@jwt_required()
def get_client(client_id):
    client = _get_client(client_id)
    if client is None:
        return jsonify({"message": "Client not found"}), 404
    contract = db.session.scalar(db.select(Contract).filter_by(
        client_id=client.id, is_active=True))
    body = client.serialize()
    body["contract"] = contract.serialize() if contract else None
    return jsonify(body), 200


@clients_bp.route("/<int:client_id>", methods=["PUT"])
@jwt_required()
def update_client(client_id):
    client = _get_client(client_id)
    if client is None:
        return jsonify({"message": "Client not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"message": "name cannot be empty"}), 400
        client.name = name
    if "tax_id" in data:
        client.tax_id = (data.get("tax_id") or "").strip() or None
    if "email" in data:
        client.email = (data.get("email") or "").strip().lower() or None
    if "is_archived" in data:
        client.is_archived = bool(data.get("is_archived"))

    db.session.commit()
    return jsonify(client.serialize()), 200


@clients_bp.route("/<int:client_id>", methods=["DELETE"])
@jwt_required()
def archive_client(client_id):
    client = _get_client(client_id)
    if client is None:
        return jsonify({"message": "Client not found"}), 404
    client.is_archived = True
    db.session.commit()
    return jsonify(client.serialize()), 200


def _to_money(value, field):
    """Turn a JSON value into a Decimal with 2 decimals, or raise ValueError."""
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        raise ValueError(f"{field} must be a number")
    if amount < 0:
        raise ValueError(f"{field} cannot be negative")
    return amount


@clients_bp.route("/<int:client_id>/contract", methods=["PUT"])
@jwt_required()
def set_contract(client_id):
    client = _get_client(client_id)
    if client is None:
        return jsonify({"message": "Client not found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        fixed_fee = _to_money(
            data.get("fixed_monthly_fee", "0"), "fixed_monthly_fee")
        vat_rate = _to_money(data.get("vat_rate", "21"), "vat_rate")
        prices = []
        seen = set()
        for item in data.get("prices") or []:
            service_id = item.get("service_id")
            if service_id in seen:
                raise ValueError(f"service {service_id} appears twice")
            seen.add(service_id)
            service = db.session.scalar(db.select(Service).filter_by(
                id=service_id, tenant_id=current_tenant_id()))
            if service is None:
                raise ValueError(f"service {service_id} not found")
            prices.append(ContractPrice(
                service=service,
                unit_price=_to_money(item.get("unit_price"), "unit_price")))
    except ValueError as error:
        return jsonify({"message": str(error)}), 400

    contract = db.session.scalar(db.select(Contract).filter_by(
        client_id=client.id, is_active=True))
    if contract is None:
        contract = Contract(client=client)
        db.session.add(contract)
    contract.fixed_monthly_fee = fixed_fee
    contract.vat_rate = vat_rate
    # Delete the old prices before inserting the new ones: SQLAlchemy would
    # otherwise INSERT first and hit the unique (contract, service) constraint.
    contract.prices.clear()
    db.session.flush()
    contract.prices = prices
    db.session.commit()
    return jsonify(contract.serialize()), 200


# --- AI: read a contract and propose its terms; the person saves ----------

CONTRACT_SYSTEM = (
    "Lees el contrato o el presupuesto de un cliente de una empresa de "
    "limpieza o mantenimiento en España y extraes las condiciones de "
    "facturación: la cuota fija mensual, el tipo de IVA y el precio de cada "
    "servicio con su unidad (hora, unidad, servicio, m²). Nunca inventes "
    "datos: si algo no aparece, déjalo vacío. No calcules nada. Responde "
    "SOLO con JSON válido, sin texto antes ni después."
)


def _contract_prompt(text, services):
    """Build the user prompt: the company's services, the catalog, the schema."""
    service_names = "\n".join(
        f"- {s.name} (unidad: {s.unit})" for s in services) or "- (ninguno)"
    catalog_names = "\n".join(f"- {name} (unidad: {unit})"
                              for name, unit in CATALOG)
    return (
        "Servicios que ya tiene la empresa (usa estos nombres exactos si "
        f"coinciden):\n{service_names}\n\n"
        "Servicios habituales del sector (usa estos nombres si el contrato "
        f"describe lo mismo):\n{catalog_names}\n\n"
        "Devuelve un objeto JSON con esta forma exacta:\n"
        '{"fixed_monthly_fee": "número o 0 si no hay cuota fija", '
        '"vat_rate": "número; 21 si no se dice", '
        '"services": [{"name": "nombre del servicio", '
        '"unit": "hora | unidad | servicio | m²", '
        '"unit_price": "número"}]}\n'
        "Una entrada por servicio con precio. Si un servicio no tiene precio "
        "claro, deja unit_price vacío.\n\n"
        f"Texto del contrato:\n\"\"\"\n{text}\n\"\"\""
    )


def _clean_price(value):
    """'28,5' -> '28.50'; anything unusable -> None."""
    try:
        amount = _parse_quantity(value)
    except InvalidOperation:
        return None
    return str(amount) if amount >= 0 else None


def _clean_contract(answer, services):
    """Re-check what the AI said: parse numbers ourselves and match each
    service against the company's services, then against the catalog."""
    answer = answer if isinstance(answer, dict) else {}
    own = _catalog(services)
    catalog = {_normalize(name): (name, unit) for name, unit in CATALOG}
    cleaned = []
    for item in answer.get("services") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        matched = _match(name, own)
        catalog_match = None if matched else _match(name, catalog)
        cleaned.append({
            "name": name,
            "unit": str(item.get("unit") or "").strip().lower() or (
                matched.unit if matched else
                catalog_match[1] if catalog_match else "unidad"),
            "unit_price": _clean_price(item.get("unit_price")),
            "exists": matched is not None,
            "service_id": matched.id if matched else None,
            "catalog_match": catalog_match[0] if catalog_match else None,
        })
    return {
        "fixed_monthly_fee": _clean_price(answer.get("fixed_monthly_fee")) or "0.00",
        "vat_rate": _clean_price(answer.get("vat_rate")) or "21.00",
        "services": cleaned,
    }


@clients_bp.route("/<int:client_id>/contract/suggest", methods=["POST"])
@jwt_required()
def suggest_contract(client_id):
    """Turn the text or a photo of a contract into contract terms to review.

    JSON {"text": ...} or multipart with "text" and/or "file" (an image).
    Writes nothing: the person reviews and presses "Guardar contrato".
    """
    client = _get_client(client_id)
    if client is None:
        return jsonify({"message": "Client not found"}), 404
    if not ai.is_configured():
        return jsonify({"message": "AI is not configured"}), 503

    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or request.form.get("text") or "").strip()
    images = []
    upload = request.files.get("file")
    if upload is not None and upload.filename:
        content = upload.read()
        if len(content) > MAX_UPLOAD_BYTES:
            return jsonify({"message": "file is too large (max 10 MB)"}), 400
        mime_type = (upload.mimetype or "").lower()
        if mime_type not in IMAGE_TYPES:
            return jsonify({"message": "file must be an image (png, jpg, webp)"}), 400
        images = [(content, mime_type)]
    if not text and not images:
        return jsonify({"message": "text or an image is required"}), 400
    if images:
        text = (text or "(sin texto)") + (
            "\n\nAdemás hay una imagen adjunta (foto o captura del contrato): "
            "lee las condiciones que aparezcan en ella.")

    services = list(db.session.scalars(db.select(Service).filter_by(
        tenant_id=current_tenant_id()).order_by(Service.name)))
    try:
        answer = ai.complete(_contract_prompt(text, services),
                             system=CONTRACT_SYSTEM, images=images)
    except ai.AIError as error:
        return jsonify({"message": f"AI provider error: {error}"}), 502
    return jsonify(_clean_contract(answer, services)), 200