import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";

export const ResetPassword = () => {
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token") || "";
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [done, setDone] = useState(false);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError(null);
        if (password !== confirm) {
            setError("Las dos contraseñas no coinciden.");
            return;
        }
        setLoading(true);
        try {
            await api("/auth/reset-password", {
                method: "POST",
                body: { token, password },
            });
            setDone(true);
        } catch (err) {
            if (err instanceof ApiError && err.status === 400) {
                setError("El enlace no es válido o ha caducado. Pide uno nuevo.");
            } else {
                setError("No hemos podido cambiar la contraseña. Inténtalo de nuevo.");
            }
        } finally {
            setLoading(false);
        }
    };

    if (done) {
        return (
            <div className="d-flex flex-column gap-3">
                <h2 className="mb-0">Contraseña cambiada</h2>
                <p className="io-muted mb-0">Ya puedes entrar con la nueva contraseña.</p>
                <Link to="/login" className="btn btn-primary">Entrar</Link>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="d-flex flex-column gap-3">
            <div>
                <h2 className="mb-1">Nueva contraseña</h2>
                <p className="io-muted mb-0">Elige una de al menos 8 caracteres</p>
            </div>

            {error && (
                <div className="alert alert-danger py-2 mb-0" role="alert">
                    {error}
                </div>
            )}

            <div>
                <label htmlFor="password" className="form-label">Contraseña nueva</label>
                <input
                    id="password"
                    type="password"
                    className="form-control"
                    autoComplete="new-password"
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                />
            </div>

            <div>
                <label htmlFor="confirm" className="form-label">Repite la contraseña</label>
                <input
                    id="confirm"
                    type="password"
                    className="form-control"
                    autoComplete="new-password"
                    minLength={8}
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    required
                />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? "Guardando…" : "Guardar contraseña"}
            </button>

            <p className="text-center io-muted mb-0">
                <Link to="/forgot-password" className="fw-semibold">Pedir otro enlace</Link>
            </p>
        </form>
    );
};