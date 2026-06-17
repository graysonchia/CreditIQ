export function currency(value: number): string {
  return new Intl.NumberFormat("en-MY", { style: "currency", currency: "MYR", maximumFractionDigits: 0 }).format(value);
}

export function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  return `${Math.round(value * 100)}%`;
}

export function compact(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact" }).format(value);
}

export function riskLevel(score: number): "Low" | "Medium" | "High" {
  if (score < 0.3) return "Low";
  if (score <= 0.7) return "Medium";
  return "High";
}

export function riskClass(level: "Low" | "Medium" | "High"): string {
  return level === "Low" ? "risk-low" : level === "Medium" ? "risk-medium" : "risk-high";
}

export function exportCsv(filename: string, rows: Record<string, unknown>[]): void {
  const headers = Object.keys(rows[0] ?? {});
  const csv = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => JSON.stringify(row[header] ?? "")).join(","))
  ].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
