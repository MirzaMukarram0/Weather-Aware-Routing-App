export type RiskLevel =
  | "LOW"
  | "MODERATE"
  | "HIGH"
  | "SEVERE"
  | "NO_TRAVEL"
  | "UNKNOWN";

export interface LocationItem {
  id: string;
  label: string;
  lat: number;
  lon: number;
}

export interface Checkpoint {
  lat: number;
  lon: number;
  distance_mi: number;
  eta_utc: string;
  weather: {
    wind_sustained_mph: number | null;
    wind_gust_mph: number | null;
    rain_in_hr: number | null;
    snow_in_hr: number | null;
  };
  risk_level: RiskLevel;
}

export interface RouteSummary {
  no_travel_mi: number;
  severe_mi: number;
  high_mi: number;
  moderate_mi: number;
  low_mi: number;
  unknown_mi: number;
  avg_risk: number | null;
  weather_complete: boolean;
}

export interface RoutePlan {
  id: string;
  distance_mi: number;
  duration_s: number;
  polyline: string;
  checkpoints: Checkpoint[];
  summary: RouteSummary;
}

export interface PlanResponse {
  departure_utc: string;
  timezone: string;
  interval_mi: number;
  warnings: string[];
  routes: RoutePlan[];
  recommendation: {
    route_id: string;
    reason: string;
    warnings: string[];
  };
}

export interface HeatmapCell {
  id: string;
  lat: number;
  lon: number;
  polygon: { lat: number; lon: number }[];
  levels_by_hour: RiskLevel[];
}

export interface HeatmapResponse {
  cell_mi: number;
  timestamps_utc: string[];
  cells: HeatmapCell[];
}

export interface PlanRequest {
  origin_lat: number;
  origin_lon: number;
  origin_label?: string;
  dest_lat: number;
  dest_lon: number;
  dest_label?: string;
  departure: string;
  timezone: string;
  load_lb: number;
  interval_mi: 10 | 25 | 50;
}
