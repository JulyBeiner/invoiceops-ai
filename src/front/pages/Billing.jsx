import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, download, errorText } from "../api";
import { euros, monthLabel, thisMonth } from "../format";

const runMonth = (run) => `${run.year}-${String(run.month).padStart(2, "0")}`;
const sum = (proposals, status) =>
  proposals.filter((p) => !status || p.status === status).reduce((acc, p) => acc + Number(p.total), 0);

export const Billing = () => {
  const [runs, setRuns] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [month, setMonth] = useState(thisMonth());
  const [closing, setClosing] = useState(false);
  const [warnings, setWarnings] = useState([]);
  const [notice, setNotice] = useState(null);

  const say = (kind, text) => {
    setNotice({ kind, text });
    setTimeout(() => setNotice(null), 6000);
  };
  const load = () =>
    api("/billing-runs").then((list) => {
      setRuns(list);
      if (list.length && !list.some((r) => r.id === selectedId)) setSelectedId(list[0].id);
      return list;
    });

  useEffect(() => { load(); }, []);

  const closeMonth = async () => {
    if (!window.confirm(`¿Cerrar ${monthLabel(month)}? Se generará una propuesta por cliente con contrato.`)) return;
    setClosing(true);
    try {
      const run = await api("/billing-runs", { method: "POST", body: { month } });
      setWarnings(run.clients_without_activity || []);
      await load();
      setSelectedId(run.id);
      say("success", `${monthLabel(month)} cerrado: ${run.proposals.length} propuestas generadas.`);
    } catch (err) {
      if (err.status === 409) say("warning", "Ese mes ya estaba cerrado.");
      else if (err.status === 400) say("warning", "No hay nada que facturar en ese mes: revisa contratos, precios y actividades.");
      else say("danger", errorText(err));
    } finally {
      setClosing(false);
    }
  };

  const exportCsv = async (run) => {
    try {
      await download(`/billing-runs/${run.id}/export.csv`, `facturacion-${runMonth(run)}.csv`);
    } catch (err) {
      say("danger", errorText(err));
    }
  };

  const selected = runs.find((r) => r.id === selectedId);
  const approved = (run) => run.proposals.filter((p) => p.status === "approved").length;

  return (
    <>
      <div className="io-page-header">
        <div>
          <h1>Cierre de mes</h1>
          <p>Genera las propuestas de cada cliente, revísalas y apruébalas</p>
        </div>
        <div className="d-flex gap-2 align-items-center">
          <input type="month" className="form-control" style={{ width: 170 }} aria-label="Mes a cerrar" value={month} onChange={(e) => setMonth(e.target.value)} />
          <button type="button" className="btn btn-primary" onClick={closeMonth} disabled={closing}>
            <i className="fa-solid fa-calendar-check me-2"></i>{closing ? "Cerrando…" : "Cerrar mes"}
          </button>
        </div>
      </div>

      {notice && <div className={`alert alert-${notice.kind} py-2 mb-0`} role="alert">{notice.text}</div>}

      {warnings.length > 0 && (
        <div className="alert alert-warning mb-0" role="alert">
          <strong>Revisa:</strong> con contrato pero sin actividad este mes:{" "}
          {warnings.map((w) => w.client_name).join(", ")}. <Link to="/activities">Ver actividades</Link>
        </div>
      )}

      <div className="card px-3 py-1">
        <table className="table table-hover">
          <thead>
            <tr><th>Mes</th><th className="text-end">Propuestas</th><th className="text-end">Aprobadas</th><th className="text-end">Total</th><th>Estado</th><th></th></tr>
          </thead>
          <tbody>
            {runs.length === 0 && (
              <tr><td colSpan="6" className="io-muted py-4 text-center">Todavía no has cerrado ningún mes. Elige el mes arriba y pulsa "Cerrar mes".</td></tr>
            )}
            {runs.map((run) => (
              <tr key={run.id} className={run.id === selectedId ? "io-selected" : ""} onClick={() => setSelectedId(run.id)} style={{ cursor: "pointer" }}>
                <td className="fw-semibold">{monthLabel(runMonth(run))}</td>
                <td className="text-end io-num">{run.proposals.length}</td>
                <td className="text-end io-num">{approved(run)}</td>
                <td className="text-end io-num">{euros(sum(run.proposals))}</td>
                <td>
                  {run.status === "closed"
                    ? <span className="io-badge io-badge-navy">Cerrado</span>
                    : <span className="io-badge io-badge-amber">En revisión</span>}
                </td>
                <td className="text-end">
                  <button type="button" className="btn btn-outline-secondary btn-sm" disabled={approved(run) === 0} onClick={(e) => { e.stopPropagation(); exportCsv(run); }}>
                    <i className="fa-solid fa-download me-1"></i>Exportar CSV
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="card px-3 py-1">
          <div className="d-flex justify-content-between align-items-center py-2">
            <h2 className="mb-0" style={{ fontSize: 18 }}>Propuestas de {monthLabel(runMonth(selected))}</h2>
            <span className="io-muted" style={{ fontSize: 13 }}>
              {approved(selected)} de {selected.proposals.length} aprobadas · {euros(sum(selected.proposals, "draft"))} pendientes
            </span>
          </div>
          <table className="table">
            <thead>
              <tr><th>Cliente</th><th className="text-end">Base</th><th className="text-end">IVA</th><th className="text-end">Total</th><th>Estado</th><th></th></tr>
            </thead>
            <tbody>
              {selected.proposals.length === 0 && (
                <tr><td colSpan="6" className="io-muted py-4 text-center">Ningún cliente tenía contrato con actividad o cuota este mes.</td></tr>
              )}
              {selected.proposals.map((p) => (
                <tr key={p.id}>
                  <td><Link to={`/proposals/${p.id}`} className="fw-semibold">{p.client_name}</Link></td>
                  <td className="text-end io-num">{euros(p.subtotal)}</td>
                  <td className="text-end io-num">{euros(p.vat_amount)}</td>
                  <td className="text-end io-num">{euros(p.total)}</td>
                  <td>
                    {p.status === "approved"
                      ? <span className="io-badge io-badge-green">Aprobada</span>
                      : <span className="io-badge io-badge-amber">Borrador</span>}
                  </td>
                  <td className="text-end">
                    <Link to={`/proposals/${p.id}`} className="btn btn-link btn-sm">Ver</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
};