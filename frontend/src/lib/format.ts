export function formatCompactNumber(value: number): string {
  if (Math.abs(value) < 1000) return String(value);
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function formatAmount(value: number | string, currency?: string): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  const formatted = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 0 }).format(num);
  return currency ? `${currency} ${formatted}` : formatted;
}

export function formatMonthLabel(isoDate: string): string {
  const d = new Date(isoDate + (isoDate.length === 10 ? "T00:00:00" : ""));
  return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}
