import type { RiskLevel } from "../types/plan";

export const LEVEL_COLORS: Record<RiskLevel, [number, number, number, number]> = {
  LOW: [34, 197, 94, 180],
  MODERATE: [234, 179, 8, 180],
  HIGH: [249, 115, 22, 190],
  SEVERE: [239, 68, 68, 200],
  NO_TRAVEL: [127, 29, 29, 220],
  UNKNOWN: [156, 163, 175, 120],
};

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

/** ponytail: minimal polyline decode, precision 5 */
export function decodePolyline(encoded: string): [number, number][] {
  let index = 0;
  const coordinates: [number, number][] = [];
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let result = 0;
    let shift = 0;
    let b: number;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += dlat;

    result = 0;
    shift = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += dlng;

    coordinates.push([lat / 1e5, lng / 1e5]);
  }
  return coordinates;
}
