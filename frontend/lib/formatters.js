export function formatFieldValue(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (typeof value === "number") {
    return new Intl.NumberFormat("en-US", {
      maximumFractionDigits: value >= 1 ? 0 : 4
    }).format(value);
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}
