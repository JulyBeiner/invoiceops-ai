import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import useGlobalReducer from "../hooks/useGlobalReducer";

export const Register = () => {
    const { dispatch } = useGlobalReducer();
    const navigate = useNavigate();
    const [form, setForm] = useState({
        company_name: "",
        full_name: "",
        email: "",
        password: "",
    });
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError(null);
        setLoading(true);
        try {
            const data = await api("/auth/register", { method: "POST", body: form });
            dispatch({ type: "login", payload: data });
            navigate("/");
        } catch (err) {
            if (err instanceof ApiError && err.status === 409) {
                setError("Ese email ya tiene una cuenta. Prueba a entrar.");
            } else if (err instanceof ApiError && err.status === 400) {
                setError("Revisa los datos: todos los campos son obligatorios y la contraseña necesita 8 caracteres.");
            } else {
                setError("No hemos podido crear la cuenta. Inténtalo de nuevo.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="d-flex flex-column gap-3">
            <div>
                <h2 className="mb-1">Crear la cuenta</h2>
                <p className="io-muted mb-0">Tu empresa y tu usuario, en un paso</p>
            </div>

            {error && (
                <div className="alert alert-danger py-2 mb-0" role="alert">
                    {error}
                </div>
            )}

            <div>
                <label htmlFor="company_name" className="form-label">Nombre de la empresa</label>
                <input
                    id="company_name"
                    className="form-control"
                    placeholder="Limpiezas Aurora S.L."
                    value={form.company_name}
                    onChange={update("company_name")}
                    required
                />
            </div>

            <div>
                <label htmlFor="full_name" className="form-label">Tu nombre</label>
                <input
                    id="full_name"
                    className="form-control"
                    autoComplete="name"
                    value={form.full_name}
                    onChange={update("full_name")}
                    required
                />
            </div>

            <div>
                <label htmlFor="email" className="form-label">Email</label>
                <input
                    id="email"
                    type="email"
                    className="form-control"
                    placeholder="tu@empresa.es"
                    autoComplete="username"
                    value={form.email}
                    onChange={update("email")}
                    required
                />
            </div>

            <div>
                <label htmlFor="password" className="form-label">Contraseña</label>
                <input
                    id="password"
                    type="password"
                    className="form-control"
                    autoComplete="new-password"
                    minLength={8}
                    value={form.password}
                    onChange={update("password")}
                    required
                />
                <div className="form-text">Mínimo 8 caracteres.</div>
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? "Creando…" : "Crear la cuenta"}
            </button>

            <p className="text-center io-muted mb-0">
                ¿Ya tienes cuenta? <Link to="/login" className="fw-semibold">Entrar</Link>
            </p>
        </form>
    );
};