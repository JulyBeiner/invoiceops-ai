from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import extract

from api.extensions import db
from api.models import Activity, Client, Service
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
