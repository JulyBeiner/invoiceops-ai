import { useEffect, useState } from "react";
import { aiError, api, errorText } from "../api";

const emptyClient = { name: "", tax_id: "", email: "" };
const toApi = (value) => String(value ?? "").trim().replace(",", ".");
const toInput = (value) => (value == null ? "" : String(value).replace(".", ","));

// Catalog of standard services of the niche: tick the ones you offer and
// they are created in one go. Existing ones are shown ticked and disabled.
const CatalogPicker = ({ onCreated, say }) => {
    const [open, setOpen] = useState(false);
    const [items, setItems] = useState([]);
    const [chosen, setChosen] = useState([]);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (open) api("/services/catalog").then((list) => { setItems(list); setChosen([]); });
    }, [open]);

    const toggle = (name) => setChosen(chosen.includes(name) ? chosen.filter((n) => n !== name) : [...chosen, name]);

    const create = async () => {
        setSaving(true);
        try {
            const result = await api("/services/catalog", { method: "POST", body: { names: chosen } });
            const n = result.created.length;
            say("success", `${n} servicio${n === 1 ? "" : "s"} creado${n === 1 ? "" : "s"}. Ponles precio en el contrato.`);
            setOpen(false);
            onCreated();
        } catch (err) {
            say("danger", errorText(err));
        } finally {
            setSaving(false);
        }
    };

    if (!open) {
        return (
            <button type="button" className="btn btn-link btn-sm p-0" onClick={() => setOpen(true)}>
                <i className="fa-solid fa-list-check me-2"></i>Añadir del catálogo del sector
            </button>
        );
    }

    return (
        <div className="d-flex flex-column gap-2">
            <span className="io-muted" style={{ fontSize: 13 }}>Marca los servicios que ofreces y se crean de golpe.</span>
            <div className="row g-1">
                {items.map((item, index) => (
                    <div key={item.name} className="col-6">
                        <div className="form-check">
                            <input
                                id={`cat-${index}`}
                                type="checkbox"
                                className="form-check-input"
                                disabled={item.exists}
                                checked={item.exists || chosen.includes(item.name)}
                                onChange={() => toggle(item.name)}
                            />
                            <label htmlFor={`cat-${index}`} className="form-check-label" style={{ fontSize: 14 }}>
                                {item.name} <span className="io-muted">/ {item.unit}</span>
                                {item.exists && <span className="io-badge io-badge-gray ms-1">ya lo tienes</span>}
                            </label>
                        </div>
                    </div>
                ))}
            </div>
            <div className="d-flex gap-2">
                <button type="button" className="btn btn-primary btn-sm" disabled={saving || chosen.length === 0} onClick={create}>
                    {saving ? "Creando…" : chosen.length === 0 ? "Crear servicios" : `Crear ${chosen.length} servicio${chosen.length === 1 ? "" : "s"}`}
                </button>
                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setOpen(false)}>Cancelar</button>
            </div>
        </div>
    );
};

// Right panel: client data, contract editor, services, archive.
const ClientDetail = ({ detail, services, onChanged, onServiceCreated, say }) => {
    const [editing, setEditing] = useState(false);
    const [form, setForm] = useState(emptyClient);
    const [fee, setFee] = useState("0");
    const [vat, setVat] = useState("21");
    const [prices, setPrices] = useState({});
    const [newService, setNewService] = useState({ name: "", unit: "hora" });
    const [saving, setSaving] = useState(false);
    // AI: read the contract (text or photo) and prefill the inputs above; nothing is saved
    const [readerOpen, setReaderOpen] = useState(false);
    const [contractText, setContractText] = useState("");
    const [contractFile, setContractFile] = useState(null);
    const [fileKey, setFileKey] = useState(0);
    const [reading, setReading] = useState(false);
    const [pending, setPending] = useState([]); // services the AI read that the company does not have yet

    useEffect(() => {
        setEditing(false);
        setReaderOpen(false);
        setContractText("");
        setContractFile(null);
        setFileKey((k) => k + 1);
        setPending([]);
        setForm({ name: detail.name, tax_id: detail.tax_id || "", email: detail.email || "" });
        const contract = detail.contract;
        setFee(toInput(contract ? contract.fixed_monthly_fee : "0"));
        setVat(toInput(contract ? contract.vat_rate : "21"));
        const map = {};
        (contract?.prices || []).forEach((p) => { map[p.service_id] = toInput(p.unit_price); });
        setPrices(map);
    }, [detail]);

    const saveClient = async (e) => {
        e.preventDefault();
        try {
            await api(`/clients/${detail.id}`, { method: "PUT", body: form });
            say("success", "Cliente guardado.");
            onChanged();
        } catch (err) {
            say("danger", errorText(err));
        }
    };

    const saveContract = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const priceList = Object.entries(prices)
                .filter(([, value]) => String(value).trim() !== "")
                .map(([service_id, value]) => ({ service_id: Number(service_id), unit_price: toApi(value) }));
            await api(`/clients/${detail.id}/contract`, {
                method: "PUT",
                body: { fixed_monthly_fee: toApi(fee || "0"), vat_rate: toApi(vat || "21"), prices: priceList },
            });
            say("success", "Contrato guardado.");
            onChanged();
        } catch (err) {
            say("danger", errorText(err));
        } finally {
            setSaving(false);
        }
    };

    const toggleArchive = async () => {
        const archive = !detail.is_archived;
        if (archive && !window.confirm(`¿Archivar a ${detail.name}? Dejará de aparecer en el cierre de mes.`)) return;
        try {
            if (archive) await api(`/clients/${detail.id}`, { method: "DELETE" });
            else await api(`/clients/${detail.id}`, { method: "PUT", body: { is_archived: false } });
            say("success", archive ? "Cliente archivado." : "Cliente reactivado.");
            onChanged();
        } catch (err) {
            say("danger", errorText(err));
        }
    };

    const readContract = async () => {
        setReading(true);
        try {
            let body = { text: contractText };
            if (contractFile) {
                body = new FormData();
                body.append("text", contractText);
                body.append("file", contractFile);
            }
            const result = await api(`/clients/${detail.id}/contract/suggest`, { method: "POST", body });
            setFee(toInput(result.fixed_monthly_fee));
            setVat(toInput(result.vat_rate));
            const map = { ...prices };
            result.services.filter((s) => s.exists).forEach((s) => { map[s.service_id] = toInput(s.unit_price); });
            setPrices(map);
            setPending(result.services.filter((s) => !s.exists));
            const found = result.services.filter((s) => s.exists).length;
            say(found > 0 || result.services.length === 0 ? "success" : "warning",
                found > 0 ? `Rellenados cuota, IVA y ${found} precios. Revisa y pulsa Guardar contrato.` : "Rellenados cuota e IVA. Los servicios leídos no existen aún: créalos abajo.");
        } catch (err) {
            say("danger", err.status === 400 ? "Pega el texto del contrato o adjunta una foto (png, jpg, webp, menos de 10 MB)." : aiError(err));
        } finally {
            setReading(false);
        }
    };

    const createPending = async (item) => {
        try {
            const created = await api("/services", { method: "POST", body: { name: item.catalog_match || item.name, unit: item.unit } });
            if (item.unit_price) setPrices((map) => ({ ...map, [created.id]: toInput(item.unit_price) }));
            setPending((list) => list.filter((p) => p !== item));
            say("success", `Servicio "${created.name}" creado con su precio. Pulsa Guardar contrato.`);
            onServiceCreated();
        } catch (err) {
            say("danger", errorText(err));
        }
    };

    const addService = async (e) => {
        e.preventDefault();
        if (!newService.name.trim()) return;
        try {
            await api("/services", { method: "POST", body: newService });
            setNewService({ name: "", unit: "hora" });
            say("success", "Servicio creado. Ponle precio en el contrato.");
            onServiceCreated();
        } catch (err) {
            say("danger", errorText(err));
        }
    };

    return (
        <div className="card p-4 d-flex flex-column gap-4">
            {editing ? (
                <form onSubmit={saveClient} className="d-flex flex-column gap-2">
                    <label className="form-label mb-0" htmlFor="c-name">Nombre</label>
                    <input id="c-name" className="form-control" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                    <label className="form-label mb-0" htmlFor="c-tax">NIF</label>
                    <input id="c-tax" className="form-control" value={form.tax_id} onChange={(e) => setForm({ ...form, tax_id: e.target.value })} />
                    <label className="form-label mb-0" htmlFor="c-email">Email</label>
                    <input id="c-email" type="email" className="form-control" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                    <div className="d-flex gap-2 mt-2">
                        <button type="submit" className="btn btn-primary btn-sm">Guardar</button>
                        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setEditing(false)}>Cancelar</button>
                    </div>
                </form>
            ) : (
                <div className="d-flex justify-content-between align-items-start gap-2">
                    <div>
                        <h2 className="mb-1" style={{ fontSize: 20 }}>{detail.name}</h2>
                        <span className="io-muted" style={{ fontSize: 13 }}>
                            {detail.tax_id || "Sin NIF"} · {detail.email || "Sin email"}
                        </span>
                    </div>
                    <button type="button" className="btn btn-link btn-sm" onClick={() => setEditing(true)}>Editar</button>
                </div>
            )}

            <form onSubmit={saveContract} className="d-flex flex-column gap-3 pt-3 border-top">
                <div className="d-flex justify-content-between align-items-center">
                    <h3 className="mb-0" style={{ fontSize: 16 }}>Contrato</h3>
                    <span className={`io-badge ${detail.contract ? "io-badge-green" : "io-badge-gray"}`}>
                        {detail.contract ? "Activo" : "Sin contrato"}
                    </span>
                </div>

                <button type="button" className="btn btn-link btn-sm p-0 align-self-start" onClick={() => setReaderOpen((v) => !v)}>
                    <i className="fa-solid fa-wand-magic-sparkles me-2"></i>{readerOpen ? "Ocultar" : "Rellenar con IA desde el contrato (texto o foto)"}
                </button>
                {readerOpen && (
                    <div className="card p-3 d-flex flex-column gap-2" style={{ background: "var(--io-lime-soft)" }}>
                        <span className="io-muted" style={{ fontSize: 13 }}>Pega el texto del contrato o del presupuesto, o adjunta una foto o captura. La IA lee y propone cuota, IVA y precios; tú revisas y guardas.</span>
                        <textarea className="form-control" rows={4} placeholder="Ejemplo: «Cuota fija 250 € al mes. Limpieza de oficina 28,50 €/hora. Cristales 45 € por unidad. IVA 21 %»" value={contractText} onChange={(e) => setContractText(e.target.value)} />
                        <div className="d-flex gap-2 align-items-center flex-wrap">
                            <input key={fileKey} type="file" className="form-control form-control-sm" style={{ maxWidth: 300 }} accept="image/png,image/jpeg,image/webp" aria-label="Foto del contrato" onChange={(e) => setContractFile(e.target.files[0] || null)} />
                            <button type="button" className="btn btn-primary btn-sm" disabled={reading || (!contractText.trim() && !contractFile)} onClick={readContract}>
                                <i className="fa-solid fa-wand-magic-sparkles me-2"></i>{reading ? "Leyendo…" : "Analizar"}
                            </button>
                        </div>
                        {pending.length > 0 && (
                            <div className="d-flex flex-column gap-1 pt-2 border-top">
                                <span className="fw-semibold" style={{ fontSize: 13 }}>Servicios del contrato que aún no tienes:</span>
                                {pending.map((item) => (
                                    <div key={item.name} className="d-flex align-items-center gap-2" style={{ fontSize: 14 }}>
                                        <span className="flex-grow-1">
                                            {item.catalog_match || item.name} <span className="io-muted">/ {item.unit}{item.unit_price ? ` · ${toInput(item.unit_price)} €` : " · sin precio claro"}</span>
                                            {item.catalog_match && item.catalog_match !== item.name && <span className="io-muted" style={{ fontSize: 12 }}> (leído: «{item.name}»)</span>}
                                        </span>
                                        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => createPending(item)}>Crear</button>
                                        <button type="button" className="btn btn-link btn-sm" onClick={() => setPending((list) => list.filter((p) => p !== item))} aria-label="Descartar"><i className="fa-solid fa-xmark"></i></button>
                                    </div>
                                ))}
                            </div>
                        )}
                        <span className="io-muted" style={{ fontSize: 12 }}>El texto y la foto se envían al proveedor de IA. Nada se guarda hasta que pulses Guardar contrato.</span>
                    </div>
                )}
                <div className="row g-2">
                    <div className="col-6">
                        <label className="form-label" htmlFor="fee">Cuota fija mensual (€)</label>
                        <input id="fee" className="form-control text-end io-num" inputMode="decimal" value={fee} onChange={(e) => setFee(e.target.value)} />
                    </div>
                    <div className="col-6">
                        <label className="form-label" htmlFor="vat">IVA (%)</label>
                        <input id="vat" className="form-control text-end io-num" inputMode="decimal" value={vat} onChange={(e) => setVat(e.target.value)} />
                    </div>
                </div>

                <span className="io-muted fw-semibold" style={{ fontSize: 13 }}>Precio por servicio</span>
                {services.length === 0 && <span className="io-muted" style={{ fontSize: 13 }}>Aún no hay servicios. Añádelos del catálogo o crea el primero abajo.</span>}
                {services.map((service) => (
                    <div key={service.id} className="d-flex align-items-center gap-2">
                        <label className="flex-grow-1 mb-0" htmlFor={`price-${service.id}`} style={{ fontSize: 14 }}>
                            {service.name} <span className="io-muted">/ {service.unit}</span>
                        </label>
                        <input
                            id={`price-${service.id}`}
                            className="form-control text-end io-num"
                            style={{ width: 110 }}
                            inputMode="decimal"
                            placeholder="Sin precio"
                            value={prices[service.id] ?? ""}
                            onChange={(e) => setPrices({ ...prices, [service.id]: e.target.value })}
                        />
                    </div>
                ))}
                <span className="io-muted" style={{ fontSize: 12 }}>Un servicio sin precio no se factura para este cliente.</span>
                <button type="submit" className="btn btn-primary align-self-end" disabled={saving}>
                    {saving ? "Guardando…" : "Guardar contrato"}
                </button>
            </form>

            <form onSubmit={addService} className="d-flex gap-2 align-items-end pt-3 border-top">
                <div className="flex-grow-1">
                    <label className="form-label" htmlFor="s-name">Nuevo servicio</label>
                    <input id="s-name" className="form-control" placeholder="Limpieza de oficina" value={newService.name} onChange={(e) => setNewService({ ...newService, name: e.target.value })} />
                </div>
                <div>
                    <label className="form-label" htmlFor="s-unit">Unidad</label>
                    <input id="s-unit" className="form-control" style={{ width: 90 }} value={newService.unit} onChange={(e) => setNewService({ ...newService, unit: e.target.value })} />
                </div>
                <button type="submit" className="btn btn-outline-secondary">Añadir</button>
            </form>
            <CatalogPicker onCreated={onServiceCreated} say={say} />

            <div className="pt-3 border-top">
                <button type="button" className="btn btn-link btn-sm p-0" style={{ color: detail.is_archived ? "var(--io-navy)" : "#9b2c1b" }} onClick={toggleArchive}>
                    {detail.is_archived ? "Reactivar cliente" : "Archivar cliente"}
                </button>
            </div>
        </div>
    );
};

export const Clients = () => {
    const [clients, setClients] = useState([]);
    const [services, setServices] = useState([]);
    const [selectedId, setSelectedId] = useState(null);
    const [detail, setDetail] = useState(null);
    const [showArchived, setShowArchived] = useState(false);
    const [creating, setCreating] = useState(false);
    const [newClient, setNewClient] = useState(emptyClient);
    const [notice, setNotice] = useState(null);

    const say = (kind, text) => {
        setNotice({ kind, text });
        setTimeout(() => setNotice(null), 4000);
    };
    const loadClients = () => api("/clients").then((list) => { setClients(list); return list; });
    const loadServices = () => api("/services").then(setServices);
    const loadDetail = () => (selectedId ? api(`/clients/${selectedId}`).then(setDetail) : setDetail(null));

    useEffect(() => {
        loadClients().then((list) => { if (list.length && !selectedId) setSelectedId(list[0].id); });
        loadServices();
    }, []);
    useEffect(() => { loadDetail(); }, [selectedId]);

    const createClient = async (e) => {
        e.preventDefault();
        try {
            const created = await api("/clients", { method: "POST", body: newClient });
            await loadClients();
            setSelectedId(created.id);
            setCreating(false);
            setNewClient(emptyClient);
            say("success", "Cliente creado. Ahora define su contrato.");
        } catch (err) {
            say("danger", errorText(err));
        }
    };

    const visible = clients.filter((c) => showArchived || !c.is_archived);
    const active = clients.filter((c) => !c.is_archived).length;

    return (
        <>
            <div className="io-page-header">
                <div>
                    <h1>Clientes</h1>
                    <p>{active} activos · {clients.length - active} archivados</p>
                </div>
                <div className="d-flex align-items-center gap-3">
                    <div className="form-check mb-0">
                        <input id="archived" type="checkbox" className="form-check-input" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
                        <label htmlFor="archived" className="form-check-label" style={{ fontSize: 14 }}>Ver archivados</label>
                    </div>
                    <button type="button" className="btn btn-primary" onClick={() => setCreating(!creating)}>
                        <i className="fa-solid fa-plus me-2"></i>Nuevo cliente
                    </button>
                </div>
            </div>

            {notice && <div className={`alert alert-${notice.kind} py-2 mb-0`} role="alert">{notice.text}</div>}

            {creating && (
                <form onSubmit={createClient} className="card p-3 d-flex flex-row gap-2 align-items-end">
                    <div className="flex-grow-1">
                        <label className="form-label" htmlFor="n-name">Nombre</label>
                        <input id="n-name" className="form-control" value={newClient.name} onChange={(e) => setNewClient({ ...newClient, name: e.target.value })} required autoFocus />
                    </div>
                    <div>
                        <label className="form-label" htmlFor="n-tax">NIF</label>
                        <input id="n-tax" className="form-control" value={newClient.tax_id} onChange={(e) => setNewClient({ ...newClient, tax_id: e.target.value })} />
                    </div>
                    <div>
                        <label className="form-label" htmlFor="n-email">Email</label>
                        <input id="n-email" type="email" className="form-control" value={newClient.email} onChange={(e) => setNewClient({ ...newClient, email: e.target.value })} />
                    </div>
                    <button type="submit" className="btn btn-primary">Crear</button>
                    <button type="button" className="btn btn-outline-secondary" onClick={() => setCreating(false)}>Cancelar</button>
                </form>
            )}

            <div className="row g-3">
                <div className="col-lg-7">
                    <div className="card px-3 py-1">
                        <table className="table table-hover">
                            <thead>
                                <tr><th>Cliente</th><th>Email</th><th>Estado</th></tr>
                            </thead>
                            <tbody>
                                {visible.length === 0 && (
                                    <tr><td colSpan="3" className="io-muted py-4 text-center">Todavía no hay clientes. Crea el primero con "Nuevo cliente".</td></tr>
                                )}
                                {visible.map((c) => (
                                    <tr key={c.id} className={c.id === selectedId ? "io-selected" : ""} onClick={() => setSelectedId(c.id)} style={{ cursor: "pointer" }}>
                                        <td>
                                            <span className="fw-semibold">{c.name}</span>
                                            <br />
                                            <span className="io-muted" style={{ fontSize: 12 }}>{c.tax_id || "Sin NIF"}</span>
                                        </td>
                                        <td className="io-muted">{c.email || "—"}</td>
                                        <td>
                                            <span className={`io-badge ${c.is_archived ? "io-badge-gray" : "io-badge-green"}`}>
                                                {c.is_archived ? "Archivado" : "Activo"}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div className="col-lg-5">
                    {detail ? (
                        <ClientDetail detail={detail} services={services} say={say}
                            onChanged={() => { loadClients(); loadDetail(); }}
                            onServiceCreated={loadServices} />
                    ) : (
                        <div className="card p-4 io-muted">Selecciona un cliente para ver su ficha y su contrato.</div>
                    )}
                </div>
            </div>
        </>
    );
};