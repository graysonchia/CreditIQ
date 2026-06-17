import { riskClass } from "../utils/format";

export function RiskBadge({ level }: { level: "Low" | "Medium" | "High" }) {
  return <span className={`risk-badge ${riskClass(level)}`}>{level}</span>;
}
