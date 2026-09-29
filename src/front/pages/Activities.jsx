import { useEffect, useState } from "react";
import { api, errorText } from "../api";
import { date, monthLabel, number, thisMonth } from "../format";

const today = () => new Date().toISOString().slice(0, 10);

// API messages (English) -> user text (Spanish)
const activityError = (message) => {
  const m = message || "";
  if (m.includes("client not found")) return "El cliente no existe: revisa el nombre.";
  if (m.includes("service not found")) return "El servicio no existe: revisa el nombre.";
  if (m.includes("performed_on")) return "Fecha no válida: usa DD/MM/AAAA o AAAA-MM-DD.";
  if (m.includes("already closed")) return "Ese mes ya está cerrado.";
  if (m.includes("quantity")) return "Cantidad no válida: debe ser mayor que 0.";
  return m || "Fila no válida.";
};

const ImportDialog = ({ onClose, onImported, say }) => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  const send = async (commit) => {
    const body = new FormData();
    body.append("file", file);
    return api(`/activities/import${commit ? "?commit=true" : ""}`, { method: "POST", body });
  };

  const choose = async (e) => {
    const chosen = e.target.files[0];
    setFile(chosen);
    setPreview(null);
    if (!chosen) return;
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", chosen);
      setPreview(await api("/activities/import", { method: "POST", body }));
    } catch (err) {
      say("danger", err.status === 400 ? "El archivo no es válido: revisa que tenga las columnas external_id, client, service, performed_on, quantity." : errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const doImport = async () => {
    setBusy(true);
    try {
      const result = await send(true);
      say("success", `${result.summary.ok} actividades importadas.`);
      onImported();
      onClose();
    } catch (err) {
      say("danger", errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const statusBadge = (row) => {
    if (row.status === "ok") return <span className="io-badge io-badge-green">Correcta</span>;
    if (row.status === "duplicate") return <span className="io-badge io-badge-gray">Duplicada</span>;
    return <span className="io-badge io-badge-red">Error</span>;
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(14, 26, 43, 0.55)", zIndex: 1050, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div className="card p-4 d-flex flex-column gap-3" role="dialog" aria-labelledby="import-title" style={{ width: 860, maxHeight: "90vh" }}>
        <div className="d-flex justify-content-between align-items-start">
          <div>
            <h2 id="import-title" className="mb-1" style={{ fontSize: 20 }}>Importar actividades desde CSV</h2>
            <span className="io-muted" style={{ fontSize: 14 }}>Revisa la vista previa. Nada se guarda hasta que pulses Importar.</span>
          </div>
          <button type="button" className="btn btn-link btn-sm" aria-label="Cerrar" onClick={onClose}><i className="fa-solid fa-xmark"></i></button>
        </div>

        <div>
          <label className="form-label" htmlFor="csv">Archivo CSV (columnas: external_id, client, service, performed_on, quantity)</label>
          <input id="csv" type="file" accept=".csv,text/csv" className="form-control" onChange={choose} />
        </div>

        {busy && <span className="io-muted">Procesando…</span>}

        {preview && (
          <>
            <div className="d-flex gap-2 align-items-center">
              <span className="fw-semibold" style={{ fontSize: 14 }}>{preview.rows.length} filas</span>
              <span className="io-badge io-badge-green">{preview.summary.ok} correctas</span>
              <span className="io-badge io-badge-red">{preview.summary.errors} con errores</span>
              <span className="io-badge io-badge-gray">{preview.summary.duplicates} duplicadas</span>
            </div>
            <div style={{ overflow: "auto", maxHeight: "45vh", border: "1px solid var(--io-border)", borderRadius: 10 }}>
              <table className="table">
                <thead><tr><th>Línea</th><th>Cliente</th><th>Servicio</th><th>Fecha</th><th className="text-end">Cantidad</th><th>Resultado</th></tr></thead>
                <tbody>
                  {preview.rows.map((row) => (
                    <tr key={row.line}>
                      <td className="io-muted">{row.line}</td>
                      <td>{row.data.client}</td>
                      <td>{row.data.service}</td>
                      <td>{row.data.performed_on}</td>
                      <td className="text-end io-num">{row.data.quantity}</td>
                      <td>
                        {statusBadge(row)}
                        {row.resolved && (row.resolved.client !== row.data.client || row.resolved.service !== row.data.service) && <div className="io-muted" style={{ fontSize: 12 }}>→ {row.resolved.client} · {row.resolved.service}</div>}
                        {row.status === "error" && <div style={{ fontSize: 12, color: "#9b2c1b" }}>{activityError(row.message)}</div>}
                        {row.status === "duplicate" && <div className="io-muted" style={{ fontSize: 12 }}>La referencia {row.data.external_id} ya existe.</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="d-flex justify-content-between align-items-center">
              <span className="io-muted" style={{ fontSize: 13 }}>Solo se importan las filas correctas; las demás se saltan.</span>
              <div className="d-flex gap-2">
                <button type="button" className="btn btn-outline-secondary" onClick={onClose}>Cancelar</button>
                <button type="button" className="btn btn-primary" disabled={busy || preview.summary.ok === 0} onClick={doImport}>
                  Importar {preview.summary.ok} actividades
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export const Activities = () => {
  const [month, setMonth] = useState(thisMonth());
  const [clientFilter, setClientFilter] = useState("");
  const [clients, setClients] = useState([]);
  const [services, setServices] = useState([]);
  const [activities, setActivities] = useState([]);
  const [form, setForm] = useState({ client_id: "", service_id: "", performed_on: today(), quantity: "1", external_id: "" });
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [notice, setNotice] = useState(null);

  const say = (kind, text) => {
    setNotice({ kind, text });
    setTimeout(() => setNotice(null), 4000);
  };
  const load = () =>
    api(`/activities?month=${month}${clientFilter ? `&client_id=${clientFilter}` : ""}`).then(setActivities);

  useEffect(() => {
    api("/clients").then((list) => setClients(list.filter((c) => !c.is_archived)));
    api("/services").then(setServices);
  }, []);
  useEffect(() => { load(); }, [month, clientFilter]);

  const nameOf = (list, id) => list.find((x) => x.id === id)?.name || "—";
  const unitOf = (id) => services.find((s) => s.id === id)?.unit || "";

  const add = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api("/activities", {
        method: "POST",
        body: { ...form, client_id: Number(form.client_id), service_id: Number(form.service_id), quantity: form.quantity.replace(",", "."), external_id: form.external_id || null },
      });
      say("success", "Actividad registrada.");
      setForm({ ...form, quantity: "1", external_id: "" });
      if (form.performed_on.slice(0, 7) !== month) setMonth(form.performed_on.slice(0, 7));
      else load();
    } catch (err) {
      say("danger", err.status === 409 ? "Esa referencia ya existe." : err.status === 400 ? activityError(err.message) : errorText(err));
    } finally {
      setSaving(false);
    }
  };

  const pending = activities.filter((a) => a.proposal_line_id === null).length;

  return (
    <>
      <div className="io-page-header">
        <div>
          <h1>Actividades</h1>
          <p>{monthLabel(month)} · {activities.length} registradas · {pending} pendientes de facturar</p>
        </div>
        <button type="button" className="btn btn-outline-secondary" onClick={() => setImporting(true)}>
          <i className="fa-solid fa-upload me-2"></i>Importar CSV
        </button>
      </div>

      {notice && <div className={`alert alert-${notice.kind} py-2 mb-0`} role="alert">{notice.text}</div>}

      <form onSubmit={add} className="card p-3 d-flex flex-row gap-2 align-items-end flex-wrap">
        <div className="flex-grow-1">
          <label className="form-label" htmlFor="a-client">Cliente</label>
          <select id="a-client" className="form-select" value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} required>
            <option value="">Elige un cliente</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div className="flex-grow-1">
          <label className="form-label" htmlFor="a-service">Servicio</label>
          <select id="a-service" className="form-select" value={form.service_id} onChange={(e) => setForm({ ...form, service_id: e.target.value })} required>
            <option value="">Elige un servicio</option>
            {services.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.unit})</option>)}
          </select>
        </div>
        <div>
          <label className="form-label" htmlFor="a-date">Fecha</label>
          <input id="a-date" type="date" className="form-control" value={form.performed_on} onChange={(e) => setForm({ ...form, performed_on: e.target.value })} required />
        </div>
        <div>
          <label className="form-label" htmlFor="a-qty">Cantidad</label>
          <input id="a-qty" className="form-control text-end io-num" style={{ width: 100 }} inputMode="decimal" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required />
        </div>
        <div>
          <label className="form-label" htmlFor="a-ref">Ref. (opcional)</label>
          <input id="a-ref" className="form-control" style={{ width: 130 }} value={form.external_id} onChange={(e) => setForm({ ...form, external_id: e.target.value })} />
        </div>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          <i className="fa-solid fa-plus me-2"></i>{saving ? "Guardando…" : "Añadir"}
        </button>
      </form>

      <div className="card px-3 py-2 d-flex flex-column gap-2">
        <div className="d-flex gap-2 align-items-center py-2">
          <input type="month" className="form-control" style={{ width: 170 }} aria-label="Mes" value={month} onChange={(e) => setMonth(e.target.value)} />
          <select className="form-select" style={{ width: 220 }} aria-label="Cliente" value={clientFilter} onChange={(e) => setClientFilter(e.target.value)}>
            <option value="">Todos los clientes</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <table className="table">
          <thead>
            <tr><th>Fecha</th><th>Cliente</th><th>Servicio</th><th className="text-end">Cantidad</th><th>Ref.</th><th>Facturación</th></tr>
          </thead>
          <tbody>
            {activities.length === 0 && (
              <tr><td colSpan="6" className="io-muted py-4 text-center">No hay actividades en este mes. Añade una arriba o importa un CSV.</td></tr>
            )}
            {activities.map((a) => (
              <tr key={a.id}>
                <td className="io-num">{date(a.performed_on)}</td>
                <td className="fw-semibold">{nameOf(clients, a.client_id)}</td>
                <td>{nameOf(services, a.service_id)}</td>
                <td className="text-end io-num">{number(a.quantity)} {unitOf(a.service_id)}</td>
                <td className="io-muted" style={{ fontSize: 12 }}>{a.external_id || "—"}</td>
                <td>
                  {a.proposal_line_id === null
                    ? <span className="io-badge io-badge-amber">Pendiente</span>
                    : <span className="io-badge io-badge-green">Facturada</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {importing && <ImportDialog onClose={() => setImporting(false)} onImported={load} say={say} />}
    </>
  );
};
