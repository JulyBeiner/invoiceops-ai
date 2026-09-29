from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from api.extensions import db
from api.models import Service
from api.routes.activities import _normalize
from api.routes.helpers import current_tenant_id

services_bp = Blueprint("services", __name__)

# Standard services of the niche (cleaning and maintenance companies in
# Spain). The user picks a subset and they are created in one go.
CATALOG = [
    ("Limpieza de oficina", "hora"),
    ("Limpieza de comunidad", "hora"),
    ("Limpieza de cristales", "unidad"),
    ("Limpieza fin de obra", "hora"),
    ("Limpieza de garaje", "servicio"),
    ("Abrillantado de suelos", "m²"),
    ("Desinfección", "servicio"),
    ("Mantenimiento general", "hora"),
    ("Jardinería", "hora"),
    ("Reposición de consumibles", "unidad"),
]


def _tenant_services():
    return db.session.scalars(
        db.select(Service)
        .filter_by(tenant_id=current_tenant_id())
        .order_by(Service.name)
    ).all()


def _existing_names():
    """Normalized names of the tenant's services, to skip duplicates."""
    return {_normalize(service.name) for service in _tenant_services()}


@services_bp.route("", methods=["GET"])
@jwt_required()
def list_services():
    return jsonify([service.serialize() for service in _tenant_services()]), 200


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


@services_bp.route("/catalog", methods=["GET"])
@jwt_required()
def list_catalog():
    existing = _existing_names()
    return jsonify([
        {"name": name, "unit": unit, "exists": _normalize(name) in existing}
        for name, unit in CATALOG
    ]), 200


@services_bp.route("/catalog", methods=["POST"])
@jwt_required()
def create_from_catalog():
    data = request.get_json(silent=True) or {}
    names = data.get("names") or []
    units = dict(CATALOG)
    unknown = [name for name in names if name not in units]
    if unknown:
        return jsonify({"message": f"unknown services: {', '.join(unknown)}"}), 400

    existing = _existing_names()
    created, skipped = [], []
    for name in names:
        if _normalize(name) in existing:
            skipped.append(name)
            continue
        service = Service(tenant_id=current_tenant_id(),
                          name=name, unit=units[name])
        db.session.add(service)
        created.append(service)
        existing.add(_normalize(name))
    db.session.commit()
    return jsonify({
        "created": [service.serialize() for service in created],
        "skipped": skipped,
    }), 201
