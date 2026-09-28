from datetime import date
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import extract, func

from api.extensions import db
from api.models import Activity, BillingRun, Client, Contract
from api.routes.billing_runs import _parse_month
from api.routes.helpers import current_tenant_id

dashboard_bp = Blueprint("dashboard", __name__)


def _count_activities(tenant_id, year, month, unbilled_only=False):
    """How many activities this tenant has in the month (all or unbilled)."""
    query = (db.select(func.count(Activity.id))
             .filter_by(tenant_id=tenant_id)
             .filter(extract("year", Activity.performed_on) == year,
                     extract("month", Activity.performed_on) == month))
    if unbilled_only:
        query = query.filter(Activity.proposal_line_id.is_(None))
    return db.session.scalar(query)


@dashboard_bp.route("", methods=["GET"])
@jwt_required()
def get_dashboard():
    tenant_id = current_tenant_id()
    today = date.today()
    try:
        year, month = _parse_month(
            request.args.get("month", f"{today.year}-{today.month:02d}"))
    except ValueError as error:
        return jsonify({"message": str(error)}), 400

    active_clients = db.session.scalar(
        db.select(func.count(Client.id)).join(Contract)
        .filter(Client.tenant_id == tenant_id, Client.is_archived.is_(False),
                Contract.is_active.is_(True)))

    contracted = db.session.scalars(
        db.select(Client).join(Contract)
        .filter(Client.tenant_id == tenant_id, Client.is_archived.is_(False),
                Contract.is_active.is_(True))
        .order_by(Client.name)).all()
    with_activity = set(db.session.scalars(
        db.select(Activity.client_id).filter_by(tenant_id=tenant_id)
        .filter(extract("year", Activity.performed_on) == year,
                extract("month", Activity.performed_on) == month)))
    without_activity = [{"client_id": c.id, "client_name": c.name}
                        for c in contracted if c.id not in with_activity]

    run = db.session.scalar(db.select(BillingRun).filter_by(
        tenant_id=tenant_id, year=year, month=month))
    counts = {"draft": 0, "approved": 0}
    totals = {"draft": Decimal("0.00"), "approved": Decimal("0.00")}
    for proposal in (run.proposals if run else []):
        counts[proposal.status] += 1
        totals[proposal.status] += proposal.total

    return jsonify({
        "month": f"{year}-{month:02d}",
        "active_clients": active_clients,
        "activities": {
            "total": _count_activities(tenant_id, year, month),
            "unbilled": _count_activities(tenant_id, year, month,
                                          unbilled_only=True),
        },
        "billing_run": {"id": run.id, "status": run.status} if run else None,
        "clients_without_activity": without_activity,
        "proposals": counts,
        "totals": {status: str(value) for status, value in totals.items()},
    }), 200