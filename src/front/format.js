// Spanish formatting helpers used by every page.
const MONTHS = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

// "580.00" -> "580,00 €"
export const euros = (value) =>
  Number(value ?? 0).toLocaleString("es-ES", {
    style: "currency",
    currency: "EUR",
  });

// "12.50" -> "12,50"
export const number = (value) =>
  Number(value ?? 0).toLocaleString("es-ES", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

// "2026-09-28" -> "28/09/2026"
export const date = (iso) => {
  if (!iso) return "";
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
};

// "2026-09" -> "Septiembre 2026"
export const monthLabel = (yearMonth) => {
  const [year, month] = yearMonth.split("-");
  const name = MONTHS[Number(month) - 1] || "";
  return `${name.charAt(0).toUpperCase()}${name.slice(1)} ${year}`;
};

// Today as "YYYY-MM", the format the API expects.
export const thisMonth = () => new Date().toISOString().slice(0, 7);
