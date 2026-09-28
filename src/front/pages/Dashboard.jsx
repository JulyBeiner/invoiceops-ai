import { useEffect, useState } from "react";
import { api } from "../api";
import { euros, monthLabel, thisMonth } from "../format";

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

export const Dashboard = () => {
    const [month, setMonth] = useState(thisMonth());
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        setData(null);
        setError(null);
        api(`/dashboard?month=${month}`)
            .then(setData)
            .catch(() => setError("No hemos podido cargar el resumen del mes."));
    }, [month]);

    const run = data?.billing_run;
    const runLabel = !data ? "" : !run ? "Sin cerrar" : run.status === "closed" ? "Cerrado" : "En revisión";
    const runBadge = !run ? "gray" : run.status === "closed" ? "navy" : "amber";

    return (
        <>
            <div className="io-page-header">
                <div>
                    <h1>Inicio</h1>
                    <p>{monthLabel(month)}</p>
                </div>
                <input
                    type="month"
                    className="form-control"
                    style={{ width: 180 }}
                    aria-label="Mes"
                    value={month}
                    onChange={(e) => setMonth(e.target.value)}
                />
            </div>

            {error && (
                <div className="alert alert-danger py-2 mb-0" role="alert">
                    {error}
                </div>
            )}

            <div className="row g-3">
                <Kpi
                    label="Actividades del mes"
                    value={data?.activities.total}
                    sub={data ? `${data.activities.unbilled} pendientes de facturar` : ""}
                    badge={data && data.activities.unbilled > 0 ? "amber" : null}
                />
                <Kpi
                    label="Clientes activos"
                    value={data?.active_clients}
                    sub="Con contrato en vigor"
                />
                <Kpi
                    label="Estado del mes"
                    value={data ? runLabel : undefined}
                    sub={data ? `${data.proposals.draft} pendientes · ${data.proposals.approved} aprobadas` : ""}
                    badge={data ? runBadge : null}
                />
                <Kpi
                    label="Aprobado este mes"
                    value={data ? euros(data.totals.approved) : undefined}
                    sub={data ? `${euros(data.totals.draft)} pendientes de aprobar` : ""}
                />
            </div>
        </>
    );
};