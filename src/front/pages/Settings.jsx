import { useEffect, useState } from "react";
import { api, errorText } from "../api";
import useGlobalReducer from "../hooks/useGlobalReducer";

// Company settings: name and NIF, printed as "Emisor" on every proposal PDF.
export const Settings = () => {
    const { store, dispatch } = useGlobalReducer();
    const [form, setForm] = useState({ name: "", tax_id: "" });
    const [saving, setSaving] = useState(false);
    const [notice, setNotice] = useState(null);

    const say = (kind, text) => {
        setNotice({ kind, text });
        setTimeout(() => setNotice(null), 4000);
    };

    useEffect(() => {
        api("/auth/tenant").then((tenant) => setForm({ name: tenant.name, tax_id: tenant.tax_id || "" }));
    }, []);

    const save = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const tenant = await api("/auth/tenant", { method: "PUT", body: form });
            setForm({ name: tenant.name, tax_id: tenant.tax_id || "" });
            if (store.user) dispatch({ type: "set_user", payload: { ...store.user, tenant_name: tenant.name } });
            say("success", "Datos de la empresa guardados.");
        } catch (err) {
            say("danger", errorText(err));
        } finally {
            setSaving(false);
        }
    };

    return (
        <>
            <div className="io-page-header">
                <div>
                    <h1>Ajustes</h1>
                    <p>Datos de tu empresa. Aparecen como emisor en las propuestas en PDF.</p>
                </div>
            </div>

            {notice && <div className={`alert alert-${notice.kind} py-2 mb-0`} role="alert">{notice.text}</div>}

            <form onSubmit={save} className="card p-4 d-flex flex-column gap-3" style={{ maxWidth: 520 }}>
                <div>
                    <label className="form-label" htmlFor="t-name">Nombre de la empresa</label>
                    <input id="t-name" className="form-control" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div>
                    <label className="form-label" htmlFor="t-tax">NIF</label>
                    <input id="t-tax" className="form-control" placeholder="B12345678" style={{ maxWidth: 200 }} value={form.tax_id} onChange={(e) => setForm({ ...form, tax_id: e.target.value })} />
                </div>
                <button type="submit" className="btn btn-primary align-self-start" disabled={saving}>
                    {saving ? "Guardando…" : "Guardar"}
                </button>
            </form>
        </>
    );
};