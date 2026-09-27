from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from api.extensions import db
from api.models import Service
from api.routes.helpers import current_tenant_id

services_bp = Blueprint("services", __name__)


@services_bp.route("", methods=["GET"])
@jwt_required()
def list_services():
    services = db.session.scalars(
        db.select(Service)
        .filter_by(tenant_id=current_tenant_id())
        .order_by(Service.name)
    ).all()
    return jsonify([service.serialize() for service in services]), 200


@services_bp.route("", methods=["POST"])
@jwt_required()
def create_service():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "name is required"}), 400

    service = Service(
        tenant_id=current_tenant_id(),
        name=name,
        unit=(data.get("unit") or "unit").strip(),
    )
    db.session.add(service)
    db.session.commit()
    return jsonify(service.serialize()), 201
