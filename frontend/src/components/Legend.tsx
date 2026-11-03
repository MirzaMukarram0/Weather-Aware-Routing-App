import type { RiskLevel } from "../types/plan";
import { LEVEL_COLORS } from "../map/utils";

const LABELS: RiskLevel[] = ["LOW", "MODERATE", "HIGH", "SEVERE", "NO_TRAVEL", "UNKNOWN"];

export function Legend() {
  return (
    <div className="legend" aria-label="Risk legend">
      {LABELS.map((level) => (
        <span key={level} className="legend-item">
          <i style={{ background: rgbaCss(LEVEL_COLORS[level]) }} />
          {level.replace("_", " ")}
        </span>
      ))}
    </div>
  );
}

function rgbaCss(c: [number, number, number, number]) {
  return `rgba(${c[0]},${c[1]},${c[2]},${(c[3] ?? 255) / 255})`;
}
