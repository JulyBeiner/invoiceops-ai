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

// Activity endpoints (manual form, CSV import, AI capture) share these messages.
export const activityError = (message) => {
  const m = message || "";
  if (m.includes("client not found")) return "El cliente no existe: revisa el nombre.";
  if (m.includes("service not found")) return "El servicio no existe: revisa el nombre.";
  if (m.includes("performed_on")) return "Fecha no válida: usa DD/MM/AAAA o AAAA-MM-DD.";
  if (m.includes("already closed")) return "Ese mes ya está cerrado.";
  if (m.includes("quantity")) return "Cantidad no válida: debe ser mayor que 0.";
  return m || "Fila no válida.";
};

// AI endpoints: 503 = no key configured on the server, 502 = the provider failed.
export const aiError = (error) => {
  if (error.status === 503) return "La IA no está configurada en este servidor.";
  if (error.status === 502) return "La IA no ha respondido bien. Inténtalo de nuevo en un momento.";
  return errorText(error);
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

// Download a file (PDF, CSV) that needs the token: fetch it, then save it.
export async function download(path, filename) {
  const response = await api(path, { raw: true });
  if (!response.ok) throw new ApiError(response.status, "download failed");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}