import type { RiskLevel } from "../types/plan";

export const LEVEL_COLORS: Record<RiskLevel, [number, number, number, number]> = {
  LOW: [28, 155, 119, 230],
  MODERATE: [215, 169, 36, 230],
  HIGH: [235, 124, 47, 240],
  SEVERE: [217, 70, 75, 240],
  NO_TRAVEL: [130, 32, 66, 250],
  UNKNOWN: [139, 151, 166, 210],
};

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
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
