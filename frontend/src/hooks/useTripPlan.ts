import { useCallback, useEffect, useRef, useState } from 'react';
import { postHeatmap, postPlan } from '../api/client';
import type { HeatmapResponse, PlanResponse } from '../types/plan';
import type { TripFormValues } from '../components/TripForm';

export function useTripPlan() {
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [trip, setTrip] = useState<TripFormValues | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [heatmapWarning, setHeatmapWarning] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => () => abortRef.current?.abort(), []);

  const planTrip = useCallback(async (values: TripFormValues) => {
    abortRef.current?.abort();
    const ac = new AbortController(); abortRef.current = ac;
    setLoading(true); setError(null); setPlan(null); setHeatmap(null); setHeatmapWarning(null); setHeatmapLoading(false);
    try {
      const result = await postPlan({
        origin_lat: values.origin.lat, origin_lon: values.origin.lon, origin_label: values.origin.label,
        dest_lat: values.destination.lat, dest_lon: values.destination.lon, dest_label: values.destination.label,
        departure: new Date(values.departureLocal).toISOString(), timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        load_lb: values.loadLb, interval_mi: values.intervalMi,
      }, ac.signal);
      if (ac.signal.aborted) return;
      setTrip(values); setPlan(result); setSelectedRouteId(result.recommendation.route_id); setLoading(false); setHeatmapLoading(true);
      try {
        const hm = await postHeatmap({ departure: result.departure_utc, timezone: result.timezone, load_lb: values.loadLb,
          routes: result.routes.map(r => ({ polyline: r.polyline })) }, ac.signal);
        if (!ac.signal.aborted) { setHeatmap(hm); setHeatmapWarning(hm.warnings?.join(' ') || null); }
      } catch (e) { if (!ac.signal.aborted) setHeatmapWarning((e as Error).message); }
    } catch (e) { if (!ac.signal.aborted) setError((e as Error).message); }
    finally { if (!ac.signal.aborted) { setLoading(false); setHeatmapLoading(false); } }
  }, []);
  return { plan, trip, heatmap, selectedRouteId, setSelectedRouteId, loading, heatmapLoading, error, heatmapWarning, planTrip };
}
