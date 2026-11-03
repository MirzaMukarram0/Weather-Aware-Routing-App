import { useCallback, useEffect, useRef, useState } from "react";
import { getHealth, postHeatmap, postPlan } from "./api/client";
import { HeatmapSlider } from "./components/HeatmapSlider";
import { Legend } from "./components/Legend";
import { RouteCards } from "./components/RouteCards";
import { TripForm, type TripFormValues } from "./components/TripForm";
import { MapView } from "./map/MapView";
import type { HeatmapResponse, PlanResponse } from "./types/plan";
import "./index.css";

function localToIso(local: string): string {
  const d = new Date(local);
  return d.toISOString();
}

export default function App() {
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [hourIndex, setHourIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    getHealth().catch(() => {
      setError("Cannot reach the API. Check VITE_API_URL and that the backend is running.");
    });
  }, []);

  const onSubmit = useCallback(async (values: TripFormValues) => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);
    setHeatmap(null);
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const body = {
        origin_lat: values.origin.lat,
        origin_lon: values.origin.lon,
        origin_label: values.origin.label,
        dest_lat: values.destination.lat,
        dest_lon: values.destination.lon,
        dest_label: values.destination.label,
        departure: localToIso(values.departureLocal),
        timezone: tz,
        load_lb: values.loadLb,
        interval_mi: values.intervalMi,
      };
      const result = await postPlan(body, ac.signal);
      setPlan(result);
      setSelectedRouteId(result.recommendation.route_id);
      setHourIndex(0);
      void postHeatmap(
        {
          departure: result.departure_utc,
          timezone: result.timezone,
          load_lb: values.loadLb,
          routes: result.routes.map((r) => ({ polyline: r.polyline })),
        },
        ac.signal,
      )
        .then(setHeatmap)
        .catch(() => {
          /* routes still usable */
        });
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setError((e as Error).message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const sliderLabel =
    heatmap?.timestamps_utc[hourIndex]?.replace("T", " ").replace("+00:00", " UTC") ??
    "loading…";

  return (
    <div className="layout">
      <aside className="sidebar">
        <TripForm loading={loading} onSubmit={onSubmit} />
        {error && <p className="banner error">{error}</p>}
        {plan && (
          <RouteCards
            plan={plan}
            selectedRouteId={selectedRouteId}
            onSelect={setSelectedRouteId}
          />
        )}
        <Legend />
        <HeatmapSlider
          hourIndex={hourIndex}
          maxHour={48}
          label={sliderLabel}
          onChange={setHourIndex}
          disabled={!heatmap}
        />
      </aside>
      <main className="map-panel">
        <MapView
          plan={plan}
          heatmap={heatmap}
          hourIndex={hourIndex}
          selectedRouteId={selectedRouteId}
          onSelectRoute={setSelectedRouteId}
        />
      </main>
    </div>
  );
}
