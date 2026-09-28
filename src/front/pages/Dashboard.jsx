import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { date, euros, monthLabel, number, thisMonth } from "../format";

const Kpi = ({ label, value, sub, badge }) => (
    <div className="col-md-6 col-xl-3">
        <div className="card h-100 p-3 d-flex flex-column gap-2">
            <span className="io-muted fw-semibold" style={{ fontSize: 13 }}>{label}</span>
            <span className="io-kpi-value io-num">{value ?? "…"}</span>
            {badge ? (
                <span className={`io-badge io-badge-${badge} align-self-start`}>{sub}</span>
            ) : (
                <span className="io-muted" style={{ fontSize: 13 }}>{sub}</span>
            )}
        </div>
    </div>
);

// One of the three steps of the month: done / current / pending.
const Step = ({ number: n, title, text, state, action }) => {
    const circle = {
        done: { background: "var(--io-lime-soft)", color: "#3b6d11" },
        current: { background: "var(--io-ink)", color: "var(--io-lime)" },
        pending: { background: "#eceef2", color: "var(--io-muted)" },
    }[state];
    return (
        <div className="d-flex gap-3 align-items-start">
            <span className="d-inline-flex align-items-center justify-content-center flex-shrink-0 fw-bold" style={{ width: 32, height: 32, borderRadius: "50%", fontSize: 14, ...circle }}>
                {state === "done" ? <i className="fa-solid fa-check"></i> : n}
            </span>
            <div className="d-flex flex-column gap-1 flex-grow-1">
                <span className="fw-semibold" style={{ fontSize: 15, color: state === "pending" ? "var(--io-muted)" : "var(--io-text)" }}>{title}</span>
                <span className="io-muted" style={{ fontSize: 14 }}>{text}</span>
                {state === "current" && action && <div className="mt-1">{action}</div>}
            </div>
        </div>
    );
};

export const Dashboard = () => {
    const [month, setMonth] = useState(thisMonth());
    const [data, setData] = useState(null);
    const [recent, setRecent] = useState([]);
    const [names, setNames] = useState({ clients: {}, services: {} });
    const [error, setError] = useState(null);

    useEffect(() => {
        api("/clients").then((list) => setNames((n) => ({ ...n, clients: Object.fromEntries(list.map((c) => [c.id, c.name])) })));
        api("/services").then((list) => setNames((n) => ({ ...n, services: Object.fromEntries(list.map((s) => [s.id, s.name])) })));
    }, []);

    useEffect(() => {
        setData(null);
        setError(null);
        api(`/dashboard?month=${month}`)
            .then(setData)
            .catch(() => setError("No hemos podido cargar el resumen del mes."));
        api(`/activities?month=${month}`)
            .then((list) => setRecent(list.slice(-5).reverse()))
            .catch(() => setRecent([]));
    }, [month]);

    const run = data?.billing_run;
    const label = monthLabel(month);
    const runLabel = !data ? "" : !run ? "Sin cerrar" : run.status === "closed" ? "Cerrado" : "En revisión";
    const runBadge = !run ? "gray" : run.status === "closed" ? "navy" : "amber";

    const hasActivity = (data?.activities.total ?? 0) > 0;
    const step1 = hasActivity ? "done" : "current";
    const step2 = run ? "done" : hasActivity ? "current" : "pending";
    const step3 = !run ? "pending" : run.status === "closed" ? "done" : "current";

    return (
        <>
            <div className="io-page-header">
                <div>
                    <h1>Inicio</h1>
                    <p>{label}</p>
                </div>
                <input type="month" className="form-control" style={{ width: 180 }} aria-label="Mes" value={month} onChange={(e) => setMonth(e.target.value)} />
            </div>

            {error && <div className="alert alert-danger py-2 mb-0" role="alert">{error}</div>}

            <div className="row g-3">
                <Kpi label="Actividades del mes" value={data?.activities.total}
                    sub={data ? `${data.activities.unbilled} pendientes de facturar` : ""}
                    badge={data && data.activities.unbilled > 0 ? "amber" : null} />
                <Kpi label="Clientes activos" value={data?.active_clients} sub="Con contrato en vigor" />
                <Kpi label="Estado del mes" value={data ? runLabel : undefined}
                    sub={data ? `${data.proposals.draft} pendientes · ${data.proposals.approved} aprobadas` : ""}
                    badge={data ? runBadge : null} />
                <Kpi label="Aprobado este mes" value={data ? euros(data.totals.approved) : undefined}
                    sub={data ? `${euros(data.totals.draft)} pendientes de aprobar` : ""} />
            </div>

            <div className="row g-3">
                <div className="col-lg-8">
                    <div className="card p-4 d-flex flex-column gap-4 h-100">
                        <h2 className="mb-0" style={{ fontSize: 18 }}>Cierre de {label.toLowerCase()}</h2>
                        <Step number={1} state={step1} title="Registrar la actividad"
                            text={data ? `${data.activities.total} actividades registradas este mes` : "…"}
                            action={<Link to="/activities" className="btn btn-primary btn-sm">Registrar actividades</Link>} />
                        <Step number={2} state={step2} title="Cerrar el mes"
                            text="Genera una propuesta por cliente aplicando su contrato. Podrás revisarlas una a una antes de aprobar."
                            action={<Link to="/billing" className="btn btn-primary btn-sm"><i className="fa-solid fa-calendar-check me-2"></i>Cerrar {label.toLowerCase()}</Link>} />
                        <Step number={3} state={step3} title="Aprobar las propuestas"
                            text={run && run.status === "closed" ? "Todas aprobadas: puedes exportar el CSV a tu programa de facturas." : "Al aprobarlas todas, el mes queda cerrado y podrás exportar el CSV."}
                            action={<Link to="/billing" className="btn btn-primary btn-sm">Revisar propuestas</Link>} />
                    </div>
                </div>
                <div className="col-lg-4">
                    <div className="card p-3 d-flex flex-column gap-2 h-100">
                        <h2 className="mb-1" style={{ fontSize: 16 }}><i className="fa-solid fa-triangle-exclamation me-2" style={{ color: "#8a5a0b" }}></i>Revisar antes de cerrar</h2>
                        {data && data.clients_without_activity.length === 0 && (
                            <span className="io-muted" style={{ fontSize: 14 }}>Todo en orden: todos los clientes con contrato tienen actividad este mes.</span>
                        )}
                        {data && data.clients_without_activity.map((c) => (
                            <div key={c.client_id} className="p-2 rounded" style={{ background: "#fdf1d6", fontSize: 14 }}>
                                <strong>{c.client_name}</strong> tiene contrato y ninguna actividad en {label.toLowerCase()}. <Link to="/activities" className="fw-semibold">Registrar</Link>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="card px-3 py-1">
                <div className="d-flex justify-content-between align-items-center py-2">
                    <h2 className="mb-0" style={{ fontSize: 16 }}>Últimas actividades</h2>
                    <Link to="/activities" className="fw-semibold" style={{ fontSize: 13 }}>Ver todas <i className="fa-solid fa-chevron-right ms-1"></i></Link>
                </div>
                <table className="table">
                    <thead><tr><th>Fecha</th><th>Cliente</th><th>Servicio</th><th className="text-end">Cantidad</th><th>Facturación</th></tr></thead>
                    <tbody>
                        {recent.length === 0 && <tr><td colSpan="5" className="io-muted py-3 text-center">Sin actividades este mes.</td></tr>}
                        {recent.map((a) => (
                            <tr key={a.id}>
                                <td className="io-num">{date(a.performed_on)}</td>
                                <td className="fw-semibold">{names.clients[a.client_id] || "—"}</td>
                                <td>{names.services[a.service_id] || "—"}</td>
                                <td className="text-end io-num">{number(a.quantity)}</td>
                                <td>{a.proposal_line_id === null ? <span className="io-badge io-badge-amber">Pendiente</span> : <span className="io-badge io-badge-green">Facturada</span>}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
};