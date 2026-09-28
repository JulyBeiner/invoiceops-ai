import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, download, errorText } from "../api";
import { date, euros, monthLabel, number } from "../format";

export const Proposal = () => {
  const { id } = useParams();
  const [proposal, setProposal] = useState(null);
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  const say = (kind, text) => {
    setNotice({ kind, text });
    setTimeout(() => setNotice(null), 6000);
  };
  const load = async () => {
    const data = await api(`/proposals/${id}`);
    setProposal(data);
    setRun(await api(`/billing-runs/${data.billing_run_id}`));
  };

  useEffect(() => { load().catch((err) => say("danger", errorText(err))); }, [id]);

  const approve = async () => {
    if (!window.confirm("¿Aprobar esta propuesta? Sus actividades quedarán bloqueadas y no podrá editarse.")) return;
    setBusy(true);
    try {
      await api(`/proposals/${id}/approve`, { method: "POST" });
      await load();
      say("success", "Propuesta aprobada.");
    } catch (err) {
      say("danger", err.status === 409 ? "Esta propuesta ya estaba aprobada." : errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const pdf = async () => {
    try {
      await download(`/proposals/${id}/pdf`, `propuesta-${id}.pdf`);
    } catch (err) {
      say("danger", errorText(err));
    }
  };

  if (!proposal) return <p className="io-muted">Cargando…</p>;

  const monthText = run ? monthLabel(`${run.year}-${String(run.month).padStart(2, "0")}`) : "";
  const annex = proposal.lines
    .flatMap((line) => line.activities.map((a) => ({ ...a, service: line.description })))
    .sort((a, b) => a.performed_on.localeCompare(b.performed_on));
  const approvedCount = run ? run.proposals.filter((p) => p.status === "approved").length : 0;
  const isApproved = proposal.status === "approved";

  return (
    <>
      <Link to="/billing" className="io-muted fw-semibold" style={{ fontSize: 13 }}>
        <i className="fa-solid fa-arrow-left me-2"></i>Cierre de mes · {monthText}
      </Link>

      <div className="io-page-header" style={{ marginTop: -8 }}>
        <div>
          <div className="d-flex align-items-center gap-2">
            <h1>{proposal.client_name}</h1>
            {isApproved
              ? <span className="io-badge io-badge-green">Aprobada</span>
              : <span className="io-badge io-badge-amber">Borrador</span>}
          </div>
          <p>Propuesta nº {proposal.id} · {monthText} · {annex.length} actividades</p>
        </div>
        <div className="d-flex gap-2">
          <button type="button" className="btn btn-outline-secondary" onClick={pdf}>
            <i className="fa-solid fa-file-pdf me-2"></i>Descargar PDF
          </button>
          {!isApproved && (
            <button type="button" className="btn btn-primary" onClick={approve} disabled={busy}>
              <i className="fa-solid fa-check me-2"></i>{busy ? "Aprobando…" : "Aprobar propuesta"}
            </button>
          )}
        </div>
      </div>

      {notice && <div className={`alert alert-${notice.kind} py-2 mb-0`} role="alert">{notice.text}</div>}

      <div className="row g-3">
        <div className="col-lg-8 d-flex flex-column gap-3">
          <div className="card px-3 pt-1 pb-3">
            <table className="table">
              <thead>
                <tr><th>Concepto</th><th className="text-end">Cantidad</th><th className="text-end">Precio</th><th className="text-end">Importe</th></tr>
              </thead>
              <tbody>
                {proposal.lines.map((line) => (
                  <tr key={line.id}>
                    <td>
                      {line.description}
                      {line.activities.length > 0 && <span className="io-muted" style={{ fontSize: 12 }}> · {line.activities.length} actividades</span>}
                    </td>
                    <td className="text-end io-num">{number(line.quantity)}</td>
                    <td className="text-end io-num">{euros(line.unit_price)}</td>
                    <td className="text-end io-num">{euros(line.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="d-flex flex-column align-items-end gap-1 pt-3 border-top io-num" style={{ fontSize: 14 }}>
              <div className="d-flex gap-4"><span className="io-muted">Base imponible</span><span style={{ width: 120, textAlign: "right" }}>{euros(proposal.subtotal)}</span></div>
              <div className="d-flex gap-4"><span className="io-muted">IVA</span><span style={{ width: 120, textAlign: "right" }}>{euros(proposal.vat_amount)}</span></div>
              <div className="d-flex gap-4 fw-bold" style={{ fontSize: 18 }}><span>Total</span><span style={{ width: 120, textAlign: "right" }}>{euros(proposal.total)}</span></div>
            </div>
          </div>

          <div className="card px-3 py-1">
            <div className="d-flex justify-content-between align-items-center py-2">
              <h2 className="mb-0" style={{ fontSize: 17 }}>Anexo: actividades facturadas</h2>
              <span className="io-muted" style={{ fontSize: 13 }}>{annex.length} actividades</span>
            </div>
            <table className="table">
              <thead><tr><th>Fecha</th><th>Servicio</th><th className="text-end">Cantidad</th><th>Ref.</th></tr></thead>
              <tbody>
                {annex.length === 0 && <tr><td colSpan="4" className="io-muted py-3 text-center">Solo cuota fija: no hay actividades este mes.</td></tr>}
                {annex.map((a) => (
                  <tr key={a.id}>
                    <td className="io-num">{date(a.performed_on)}</td>
                    <td>{a.service}</td>
                    <td className="text-end io-num">{number(a.quantity)}</td>
                    <td className="io-muted" style={{ fontSize: 12 }}>{a.external_id || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="col-lg-4 d-flex flex-column gap-3">
          <div className="card p-3 d-flex flex-column gap-2">
            <h2 className="mb-1" style={{ fontSize: 16 }}>
              <i className="fa-solid fa-lock me-2"></i>{isApproved ? "Propuesta aprobada" : "Antes de aprobar"}
            </h2>
            <ul className="mb-0 ps-3 d-flex flex-column gap-2" style={{ fontSize: 14 }}>
              <li>Sus {annex.length} actividades quedan bloqueadas: no se facturarán dos veces.</li>
              <li>Una propuesta aprobada no se puede editar.</li>
              <li>{run && approvedCount === run.proposals.length
                ? "Todas las propuestas del mes están aprobadas: el mes está cerrado y puedes exportar el CSV."
                : `Cuando apruebes las ${run ? run.proposals.length : ""} propuestas, el mes quedará cerrado y podrás exportar el CSV.`}</li>
            </ul>
          </div>
          <div className="card p-3 d-flex flex-column gap-1" style={{ fontSize: 14 }}>
            <h2 className="mb-1" style={{ fontSize: 16 }}>Cliente</h2>
            <span>{proposal.client_name}</span>
            <Link to="/clients" className="fw-semibold" style={{ fontSize: 13 }}>Ver ficha del cliente <i className="fa-solid fa-chevron-right ms-1"></i></Link>
          </div>
        </div>
      </div>
    </>
  );
};