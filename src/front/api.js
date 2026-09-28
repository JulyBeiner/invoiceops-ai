// Talks to the Flask API. Every page uses this instead of fetch directly.
const TOKEN_KEY = "invoiceops_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Spanish text for the user, chosen by status code (API messages are English).
export const errorText = (error) => {
  const byStatus = {
    400: "Revisa los datos: hay algún campo incorrecto.",
    401: "Tu sesión no es válida. Vuelve a entrar.",
    404: "No lo encontramos.",
    409: "Ya existe o ya se hizo.",
  };
  return byStatus[error.status] || "Algo ha fallado. Inténtalo de nuevo.";
};

// api("/clients") → GET; api("/clients", { method: "POST", body: {...} }) → POST with JSON.
// raw: true returns the Response as is (for PDF and CSV downloads).
export async function api(path, { method = "GET", body, raw = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const options = { method, headers };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`/api${path}`, options);
  if (raw) return response;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, data?.message || response.statusText);
  }
  return data;
}
