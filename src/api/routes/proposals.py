from io import BytesIO

from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required

from api.extensions import db
from api.models import BillingRun, Proposal, Tenant
from api.routes.helpers import current_tenant_id
from api.services import ai
from api.services.pdf import MONTHS, build_proposal_pdf

proposals_bp = Blueprint("proposals", __name__)


def _get_proposal(proposal_id, tenant_id):
    """Return the Proposal with that id inside this tenant, or None."""
    return db.session.scalar(
        db.select(Proposal).join(BillingRun)
        .filter(Proposal.id == proposal_id, BillingRun.tenant_id == tenant_id))


def _serialize_with_activities(proposal):
    """Proposal JSON where every line carries its full activities (the annex)."""
    data = proposal.serialize()
    for line_data, line in zip(data["lines"], proposal.lines):
        activities = sorted(line.activities,
                            key=lambda a: (a.performed_on, a.id))
        line_data["activities"] = [a.serialize() for a in activities]
    return data


@proposals_bp.route("/<int:proposal_id>", methods=["GET"])
@jwt_required()
def get_proposal(proposal_id):
    proposal = _get_proposal(proposal_id, current_tenant_id())
    if proposal is None:
        return jsonify({"message": "proposal not found"}), 404
    return jsonify(_serialize_with_activities(proposal)), 200


@proposals_bp.route("/<int:proposal_id>/approve", methods=["POST"])
@jwt_required()
def approve_proposal(proposal_id):
    proposal = _get_proposal(proposal_id, current_tenant_id())
    if proposal is None:
        return jsonify({"message": "proposal not found"}), 404
    if proposal.status == "approved":
        return jsonify({"message": "proposal is already approved"}), 409

    proposal.status = "approved"
    run = proposal.billing_run
    if all(p.status == "approved" for p in run.proposals):
        run.status = "closed"
    db.session.commit()
    return jsonify(_serialize_with_activities(proposal)), 200


@proposals_bp.route("/<int:proposal_id>/pdf", methods=["GET"])
@jwt_required()
def download_proposal_pdf(proposal_id):
    proposal = _get_proposal(proposal_id, current_tenant_id())
    if proposal is None:
        return jsonify({"message": "proposal not found"}), 404

    run = proposal.billing_run
    tenant = db.session.get(Tenant, run.tenant_id)
    filename = f"propuesta-{run.year}-{run.month:02d}-{proposal.id}.pdf"
    return send_file(BytesIO(build_proposal_pdf(tenant, proposal)),
                     mimetype="application/pdf", as_attachment=True,
                     download_name=filename)


# --- AI explanation: the AI explains and drafts; it never calculates -------

EXPLAIN_SYSTEM = (
    "Explicas una propuesta de facturación a la persona que la revisa y "
    "redactas el correo para su cliente. Usa exactamente los importes y "
    "cantidades dados: no calcules, no redondees ni inventes nada. Escribe "
    "los importes al estilo español, con coma decimal y el símbolo €, por "
    "ejemplo 782,50 €. Es una propuesta de facturación, no una factura: usa "
    "siempre la palabra propuesta, nunca factura. Responde "
    "SOLO con JSON válido con esta forma exacta: "
    '{"summary": "3 o 4 frases en español que expliquen qué se factura y por '
    'qué", "email_subject": "asunto del correo", "email_body": "correo '
    'cordial en español, con saludo, resumen de lo facturado, el total y '
    'despedida"}'
)


def _explain_prompt(tenant, proposal):
    """The proposal as plain text, with every figure already computed."""
    run = proposal.billing_run
    period = f"{MONTHS[run.month - 1]} {run.year}"
    lines = []
    for line in proposal.lines:
        dates = sorted({a.performed_on for a in line.activities})
        when = (" · fechas: " + ", ".join(d.strftime("%d/%m") for d in dates)
                if dates else "")
        lines.append(f"- {line.description} · cantidad {line.quantity} · "
                     f"precio unitario {line.unit_price} EUR · importe "
                     f"{line.amount} EUR{when}")
    status = "aprobada" if proposal.status == "approved" else "pendiente de aprobar"
    return (
        f"Empresa que factura: {tenant.name}\n"
        f"Cliente: {proposal.client.name}\n"
        f"Periodo: {period}\n"
        f"Estado: {status}\n\n"
        "Líneas:\n" + ("\n".join(lines) or "- (sin líneas)") + "\n\n"
        f"Base imponible: {proposal.subtotal} EUR\n"
        f"IVA: {proposal.vat_amount} EUR\n"
        f"Total: {proposal.total} EUR\n"
    )


@proposals_bp.route("/<int:proposal_id>/explain", methods=["GET"])
@jwt_required()
def explain_proposal(proposal_id):
    """Plain-language summary of the proposal and a draft email for the client.

    Reads only; the figures come from the billing engine, the AI only words them.
    """
    proposal = _get_proposal(proposal_id, current_tenant_id())
    if proposal is None:
        return jsonify({"message": "proposal not found"}), 404
    if not ai.is_configured():
        return jsonify({"message": "AI is not configured"}), 503

    tenant = db.session.get(Tenant, proposal.billing_run.tenant_id)
    try:
        answer = ai.complete(_explain_prompt(tenant, proposal),
                             system=EXPLAIN_SYSTEM)
    except ai.AIError as error:
        return jsonify({"message": f"AI provider error: {error}"}), 502

    answer = answer if isinstance(answer, dict) else {}
    return jsonify({
        "summary": str(answer.get("summary") or "").strip(),
        "email_subject": str(answer.get("email_subject") or "").strip(),
        "email_body": str(answer.get("email_body") or "").strip(),
    }), 200
