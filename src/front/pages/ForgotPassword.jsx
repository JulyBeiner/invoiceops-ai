import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api("/auth/forgot-password", { method: "POST", body: { email } });
      setSent(true);
    } catch (err) {
      setError("No hemos podido enviar el email. Inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="d-flex flex-column gap-3">
        <h2 className="mb-0">Revisa tu correo</h2>
        <p className="io-muted mb-0">
          Si <strong>{email}</strong> tiene cuenta, te hemos enviado un enlace para
          crear una contraseña nueva. Caduca en 1 hora.
        </p>
        <Link to="/login" className="btn btn-outline-secondary">Volver a entrar</Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="d-flex flex-column gap-3">
      <div>
        <h2 className="mb-1">¿Has olvidado la contraseña?</h2>
        <p className="io-muted mb-0">Te enviamos un enlace para crear una nueva</p>
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

      <button type="submit" className="btn btn-primary" disabled={loading}>
        {loading ? "Enviando…" : "Enviar enlace"}
      </button>

      <p className="text-center io-muted mb-0">
        <Link to="/login" className="fw-semibold">Volver a entrar</Link>
      </p>
    </form>
  );
};