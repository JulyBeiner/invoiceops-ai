import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import useGlobalReducer from "../hooks/useGlobalReducer";

export const Login = () => {
    const { dispatch } = useGlobalReducer();
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError(null);
        setLoading(true);
        try {
            const data = await api("/auth/login", {
                method: "POST",
                body: { email, password },
            });
            dispatch({ type: "login", payload: data });
            navigate("/");
        } catch (err) {
            if (err instanceof ApiError && err.status === 401) {
                setError("Email o contraseña incorrectos.");
            } else {
                setError("No hemos podido entrar. Inténtalo de nuevo.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="d-flex flex-column gap-3">
            <div>
                <h2 className="mb-1">Entrar</h2>
                <p className="io-muted mb-0">Accede a la cuenta de tu empresa</p>
            </div>

            {error && (
                <div className="alert alert-danger py-2 mb-0" role="alert">
                    {error}
                </div>
            )}

            <div>
                <label htmlFor="email" className="form-label">Email</label>
                <input
                    id="email"
                    type="email"
                    className="form-control"
                    placeholder="tu@empresa.es"
                    autoComplete="username"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                />
            </div>

            <div>
                <div className="d-flex justify-content-between align-items-baseline">
                    <label htmlFor="password" className="form-label">Contraseña</label>
                    <Link to="/forgot-password" className="small fw-semibold">¿La has olvidado?</Link>
                </div>
                <input
                    id="password"
                    type="password"
                    className="form-control"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? "Entrando…" : "Entrar"}
            </button>

            <p className="text-center io-muted mb-0">
                ¿Todavía no tienes cuenta?{" "}
                <Link to="/register" className="fw-semibold">Crear la cuenta de tu empresa</Link>
            </p>
        </form>
    );
};