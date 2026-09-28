import csv
from datetime import date
from io import StringIO

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import extract

from api.extensions import db
from api.models import (Activity, BillingRun, Client, Contract, Proposal,
                        ProposalLine)
from api.routes.helpers import current_tenant_id
from api.services.billing import build_proposal

billing_runs_bp = Blueprint("billing_runs", __name__)

CSV_COLUMNS = ["Cliente", "NIF", "Periodo", "Concepto", "Cantidad",
               "Precio unitario", "Importe", "Base imponible", "IVA", "Total"]


def _decimal_es(value):
    """Decimal('580.00') -> '580,00' (Spanish decimal comma)."""
    return f"{value:.2f}".replace(".", ",")


def _parse_month(value):
    """Turn 'YYYY-MM' into (year, month) or raise ValueError."""
    try:
        parsed = date.fromisoformat(f"{value}-01")
    except (ValueError, TypeError):
        raise ValueError("month must be a month (YYYY-MM)")
    return parsed.year, parsed.month


def _unbilled_activities(tenant_id, client_id, year, month):
    """Activities of one client in one month that have no proposal line yet."""
    return db.session.scalars(
        db.select(Activity)
        .filter_by(tenant_id=tenant_id, client_id=client_id,
                   proposal_line_id=None)
        .filter(extract("year", Activity.performed_on) == year,
                extract("month", Activity.performed_on) == month)
        .order_by(Activity.performed_on, Activity.id)
    ).all()


def _build_client_proposal(client, contract, activities):
    """Run the engine for one client; return a Proposal or None."""
    result = build_proposal(
        {
            "fixed_monthly_fee": contract.fixed_monthly_fee,
            "vat_rate": contract.vat_rate,
            "prices": {p.service_id: p.unit_price for p in contract.prices},
        },
        [{"id": a.id, "service_id": a.service_id,
          "service_name": a.service.name, "quantity": a.quantity}
         for a in activities],
    )
    if not result["lines"]:
        return None

    by_id = {a.id: a for a in activities}
    proposal = Proposal(
        client=client, subtotal=result["subtotal"],
        vat_amount=result["vat_amount"], total=result["total"])
    for line in result["lines"]:
        proposal_line = ProposalLine(
            service_id=line["service_id"], description=line["description"],
            quantity=line["quantity"], unit_price=line["unit_price"],
            amount=line["amount"])
        proposal_line.activities = [by_id[i] for i in line["activity_ids"]]
        proposal.lines.append(proposal_line)
    return proposal


def _get_run(run_id, tenant_id):
    """Return the BillingRun with that id inside this tenant, or None."""
    return db.session.scalar(db.select(BillingRun).filter_by(
        id=run_id, tenant_id=tenant_id))


@billing_runs_bp.route("", methods=["GET"])
@jwt_required()
def list_billing_runs():
    tenant_id = current_tenant_id()
    runs = db.session.scalars(
        db.select(BillingRun).filter_by(tenant_id=tenant_id)
        .order_by(BillingRun.year.desc(), BillingRun.month.desc())).all()
    return jsonify([run.serialize() for run in runs]), 200


@billing_runs_bp.route("/<int:run_id>", methods=["GET"])
@jwt_required()
def get_billing_run(run_id):
    run = _get_run(run_id, current_tenant_id())
    if run is None:
        return jsonify({"message": "billing run not found"}), 404
    return jsonify(run.serialize()), 200


@billing_runs_bp.route("/<int:run_id>/export.csv", methods=["GET"])
@jwt_required()
def export_billing_run_csv(run_id):
    run = _get_run(run_id, current_tenant_id())
    if run is None:
        return jsonify({"message": "billing run not found"}), 404

    period = f"{run.year}-{run.month:02d}"
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for proposal in run.proposals:
        if proposal.status != "approved":
            continue
        for line in proposal.lines:
            writer.writerow([
                proposal.client.name, proposal.client.tax_id or "", period,
                line.description, _decimal_es(line.quantity),
                _decimal_es(line.unit_price), _decimal_es(line.amount),
                _decimal_es(proposal.subtotal),
                _decimal_es(proposal.vat_amount), _decimal_es(proposal.total),
            ])

    filename = f"facturacion-{period}.csv"
    return Response(buffer.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"})


@billing_runs_bp.route("", methods=["POST"])
@jwt_required()
def close_month():
    tenant_id = current_tenant_id()
    data = request.get_json(silent=True) or {}
    try:
        year, month = _parse_month(data.get("month"))
    except ValueError as error:
        return jsonify({"message": str(error)}), 400

    existing = db.session.scalar(db.select(BillingRun).filter_by(
        tenant_id=tenant_id, year=year, month=month))
    if existing is not None:
        return jsonify({"message": f"{year}-{month:02d} is already closed",
                        "billing_run_id": existing.id}), 409

    run = BillingRun(tenant_id=tenant_id, year=year, month=month)
    without_activity = []
    clients = db.session.scalars(
        db.select(Client).filter_by(tenant_id=tenant_id, is_archived=False)
        .order_by(Client.name)).all()
    for client in clients:
        contract = db.session.scalar(db.select(Contract).filter_by(
            client_id=client.id, is_active=True))
        if contract is None:
            continue
        activities = _unbilled_activities(tenant_id, client.id, year, month)
        if not activities:
            without_activity.append(
                {"client_id": client.id, "client_name": client.name})
        proposal = _build_client_proposal(client, contract, activities)
        if proposal is not None:
            run.proposals.append(proposal)

    db.session.add(run)
    db.session.commit()
    body = run.serialize()
    body["clients_without_activity"] = without_activity
    return jsonify(body), 201
