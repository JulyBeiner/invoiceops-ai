from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from api.extensions import db
from api.models import Client, Contract, ContractPrice, Service
from api.routes.helpers import current_tenant_id

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
    contract.prices = prices
    db.session.commit()
    return jsonify(contract.serialize()), 200
