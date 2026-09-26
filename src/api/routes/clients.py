from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from api.extensions import db
from api.models import Client
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
