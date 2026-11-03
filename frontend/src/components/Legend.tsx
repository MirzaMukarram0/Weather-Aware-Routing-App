import type { RiskLevel } from "../types/plan";
import { LEVEL_COLORS } from "../map/utils";

const LABELS: { level: RiskLevel; label: string }[] = [
  { level: "LOW", label: "Low" },
  { level: "MODERATE", label: "Moderate" },
  { level: "HIGH", label: "High" },
  { level: "SEVERE", label: "Severe" },
  { level: "NO_TRAVEL", label: "No travel" },
  { level: "UNKNOWN", label: "Unknown" },
];

export function Legend() {
  return (
    <ul className="legend" aria-label="Risk legend">
      {LABELS.map(({ level, label }) => (
        <li key={level} className="legend__item">
          <span className="legend__swatch" style={{ background: rgbaCss(LEVEL_COLORS[level]) }} />
          {label}
        </li>
      ))}
    </ul>
  );
}

function rgbaCss(c: [number, number, number, number]) {
  return `rgba(${c[0]},${c[1]},${c[2]},${(c[3] ?? 255) / 255})`;
}
