import { useState } from "react";
import { activityError, aiError, api } from "../api";

// The AI reads and proposes; the person confirms. This panel sends free text
// (WhatsApp messages, notes) to /activities/suggest, shows the suggestions as
// editable rows and creates only the ticked ones through POST /activities.

const CONFIDENCE = {
    high: { css: "io-badge-green", label: "Segura" },
    medium: { css: "io-badge-amber", label: "Revisar" },
    low: { css: "io-badge-red", label: "Incompleta" },
};

const toRow = (suggestion, index) => ({
    key: index,
    client_id: suggestion.resolved.client_id ? String(suggestion.resolved.client_id) : "",
    service_id: suggestion.resolved.service_id ? String(suggestion.resolved.service_id) : "",
    performed_on: suggestion.performed_on || "",
    quantity: suggestion.quantity || "",
    external_id: suggestion.external_id || "",
    note: suggestion.note || "",
    read: { client: suggestion.client, service: suggestion.service },
    confidence: suggestion.confidence,
    checked: suggestion.confidence !== "low",
    error: null,
});

export const AiCapture = ({ clients, services, say, onCreated, onClose }) => {
    const [text, setText] = useState("");
    const [rows, setRows] = useState(null);
    const [busy, setBusy] = useState(false);

    const analyze = async () => {
        setBusy(true);
        setRows(null);
        try {
            const result = await api("/activities/suggest", { method: "POST", body: { text } });
            setRows(result.suggestions.map(toRow));
            if (result.suggestions.length === 0) say("warning", "La IA no ha encontrado actividades en ese texto.");
        } catch (err) {
            say("danger", aiError(err));
        } finally {
            setBusy(false);
        }
    };

    const update = (key, changes) =>
        setRows(rows.map((row) => (row.key === key ? { ...row, ...changes, error: null } : row)));

    const chosen = (rows || []).filter((row) => row.checked);

    const create = async () => {
        setBusy(true);
        let created = 0;
        const remaining = [];
        for (const row of rows) {
            if (!row.checked) {
                remaining.push(row);
                continue;
            }
            try {
                await api("/activities", {
                    method: "POST",
                    body: {
                        client_id: Number(row.client_id),
                        service_id: Number(row.service_id),
                        performed_on: row.performed_on,
                        quantity: row.quantity.replace(",", "."),
                        external_id: row.external_id || null,
                    },
                });
                created += 1;
            } catch (err) {
                const error = err.status === 409 ? "Esa referencia ya existe." : err.status === 400 ? activityError(err.message) : aiError(err);
                remaining.push({ ...row, error });
            }
        }
        setRows(remaining);
        setBusy(false);
        if (created > 0) {
            say("success", `${created} actividades creadas.`);
            onCreated();
        }
        if (remaining.length === 0) {
            setText("");
            setRows(null);
        }
    };

    return (
        <div className="card p-3 d-flex flex-column gap-3">
            <div className="d-flex justify-content-between align-items-start">
                <div>
                    <h2 className="mb-1" style={{ fontSize: 18 }}><i className="fa-solid fa-wand-magic-sparkles me-2"></i>Sugerir con IA</h2>
                    <span className="io-muted" style={{ fontSize: 14 }}>Pega los mensajes de tus trabajadores. La IA propone; tú revisas y confirmas. Nada se guarda hasta que pulses Crear.</span>
                </div>
                <button type="button" className="btn btn-link btn-sm" aria-label="Cerrar" onClick={onClose}><i className="fa-solid fa-xmark"></i></button>
            </div>

            <textarea
                className="form-control"
                rows={5}
                placeholder="Pega aquí los WhatsApps de la semana… Ejemplo: «Lunes 3,5 h en Oficinas Sol, Ana» · «Ayer cristales en el gimnasio, 1 servicio, Luis»"
                value={text}
                onChange={(e) => setText(e.target.value)}
            />
            <div className="d-flex gap-2 align-items-center">
                <button type="button" className="btn btn-primary" disabled={busy || !text.trim()} onClick={analyze}>
                    <i className="fa-solid fa-wand-magic-sparkles me-2"></i>{busy && !rows ? "Analizando…" : "Analizar"}
                </button>
                <span className="io-muted" style={{ fontSize: 13 }}>Los nombres y mensajes se envían al proveedor de IA para analizarlos.</span>
            </div>

            {rows && rows.length > 0 && (
                <>
                    <div style={{ overflow: "auto", border: "1px solid var(--io-border)", borderRadius: 10 }}>
                        <table className="table mb-0">
                            <thead>
                                <tr><th></th><th>Cliente</th><th>Servicio</th><th>Fecha</th><th className="text-end">Cantidad</th><th>Ref.</th><th>Confianza</th></tr>
                            </thead>
                            <tbody>
                                {rows.map((row) => (
                                    <tr key={row.key} style={{ opacity: row.checked ? 1 : 0.55 }}>
                                        <td>
                                            <input type="checkbox" className="form-check-input" aria-label="Crear esta actividad" checked={row.checked} onChange={(e) => update(row.key, { checked: e.target.checked })} />
                                        </td>
                                        <td style={{ minWidth: 180 }}>
                                            <select className="form-select form-select-sm" value={row.client_id} onChange={(e) => update(row.key, { client_id: e.target.value })}>
                                                <option value="">Elige un cliente</option>
                                                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                                            </select>
                                            {!row.client_id && row.read.client && <div className="io-muted" style={{ fontSize: 12 }}>La IA leyó: «{row.read.client}»</div>}
                                        </td>
                                        <td style={{ minWidth: 180 }}>
                                            <select className="form-select form-select-sm" value={row.service_id} onChange={(e) => update(row.key, { service_id: e.target.value })}>
                                                <option value="">Elige un servicio</option>
                                                {services.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.unit})</option>)}
                                            </select>
                                            {!row.service_id && row.read.service && <div className="io-muted" style={{ fontSize: 12 }}>La IA leyó: «{row.read.service}»</div>}
                                        </td>
                                        <td>
                                            <input type="date" className="form-control form-control-sm" value={row.performed_on} onChange={(e) => update(row.key, { performed_on: e.target.value })} />
                                        </td>
                                        <td>
                                            <input className="form-control form-control-sm text-end io-num" style={{ width: 90 }} inputMode="decimal" value={row.quantity} onChange={(e) => update(row.key, { quantity: e.target.value })} />
                                        </td>
                                        <td>
                                            <input className="form-control form-control-sm" style={{ width: 110 }} value={row.external_id} onChange={(e) => update(row.key, { external_id: e.target.value })} />
                                        </td>
                                        <td>
                                            <span className={`io-badge ${CONFIDENCE[row.confidence].css}`}>{CONFIDENCE[row.confidence].label}</span>
                                            {row.note && <div className="io-muted" style={{ fontSize: 12, maxWidth: 200 }}>{row.note}</div>}
                                            {row.error && <div style={{ fontSize: 12, color: "#9b2c1b" }}>{row.error}</div>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <div className="d-flex justify-content-between align-items-center">
                        <span className="io-muted" style={{ fontSize: 13 }}>Revisa cada fila: puedes cambiar cliente, servicio, fecha y cantidad antes de crear.</span>
                        <button
                            type="button"
                            className="btn btn-primary"
                            disabled={busy || chosen.length === 0 || chosen.some((row) => !row.client_id || !row.service_id || !row.performed_on || !row.quantity)}
                            onClick={create}
                        >
                            <i className="fa-solid fa-check me-2"></i>{busy ? "Creando…" : `Crear ${chosen.length} actividades`}
                        </button>
                    </div>
                </>
            )}
        </div>
    );
};