"""Build the PDF of a billing proposal (texts in Spanish: the client reads it)."""
from fpdf import FPDF

MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
STATUS = {"draft": "Borrador", "approved": "Aprobada"}


def euros(value):
    """Decimal('580.00') -> '580,00 EUR' (Spanish format; € needs a Unicode font)."""
    return f"{value:.2f}".replace(".", ",") + " EUR"


def _table(pdf, headers, rows, widths, aligns):
    """Draw one table: a header row plus one row per item."""
    with pdf.table(col_widths=widths, text_align=aligns,
                   line_height=6, padding=1) as table:
        header = table.row()
        for text in headers:
            header.cell(text)
        for row in rows:
            cells = table.row()
            for text in row:
                cells.cell(text)


def build_proposal_pdf(tenant, proposal):
    """Return the PDF bytes of one proposal, with its activity annex."""
    run = proposal.billing_run
    period = f"{MONTHS[run.month - 1]} {run.year}"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Propuesta de facturación", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Nº {proposal.id} · Periodo: {period} · "
             f"Estado: {STATUS.get(proposal.status, proposal.status)}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(95, 6, "Emisor", new_x="RIGHT")
    pdf.cell(95, 6, "Cliente", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, tenant.name, new_x="RIGHT")
    pdf.cell(95, 6, proposal.client.name, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, f"NIF: {tenant.tax_id or '-'}", new_x="RIGHT")
    pdf.cell(95, 6, f"NIF: {proposal.client.tax_id or '-'}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    _table(pdf, ["Concepto", "Cantidad", "Precio unitario", "Importe"],
           [[line.description, f"{line.quantity:.2f}".replace(".", ","),
             euros(line.unit_price), euros(line.amount)]
            for line in proposal.lines],
           widths=(85, 30, 40, 35), aligns=("LEFT", "RIGHT", "RIGHT", "RIGHT"))
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    for label, value in [("Base imponible", euros(proposal.subtotal)),
                         ("IVA", euros(proposal.vat_amount)),
                         ("Total", euros(proposal.total))]:
        if label == "Total":
            pdf.set_font("Helvetica", "B", 11)
        pdf.cell(155, 6, label, align="R", new_x="RIGHT")
        pdf.cell(35, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    activities = [(a.performed_on, line.description, a.quantity)
                  for line in proposal.lines for a in line.activities]
    if activities:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Anexo: detalle de actividades",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        _table(pdf, ["Fecha", "Servicio", "Cantidad"],
               [[day.strftime("%d/%m/%Y"), name,
                 f"{quantity:.2f}".replace(".", ",")]
                for day, name, quantity in sorted(activities)],
               widths=(40, 110, 40), aligns=("LEFT", "LEFT", "RIGHT"))
        pdf.ln(6)

    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Documento generado por InvoiceOps. Es una propuesta de "
             "facturación, no una factura.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())