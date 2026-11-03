import { useEffect, useState } from 'react';
import type { HeatmapResponse, PlanResponse } from '../types/plan';
import type { TripFormValues } from '../components/TripForm';
import { MapView } from './MapView';
import { Legend } from '../components/Legend';
import { HeatmapSlider } from '../components/HeatmapSlider';
import { formatDuration } from './utils';

interface Props {
  plan: PlanResponse | null; trip: TripFormValues | null; heatmap: HeatmapResponse | null;
  selectedRouteId: string | null; onSelectRoute: (id: string) => void;
  loading: boolean; heatmapLoading: boolean; heatmapWarning: string | null;
}
export function MapWorkspace(props: Props) {
  const { plan, trip, heatmap, selectedRouteId, onSelectRoute, loading, heatmapLoading, heatmapWarning } = props;
  const [hour, setHour] = useState(0);
  const [weatherVisible, setWeatherVisible] = useState(true);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    if (!playing || !heatmap) return;
    const timer = window.setInterval(() => setHour(h => h >= 48 ? 0 : h + 1), 900);
    return () => window.clearInterval(timer);
  }, [playing, heatmap]);
  const route = plan?.routes.find(r => r.id === selectedRouteId);
  const date = heatmap?.timestamps_utc[hour];
  const label = date ? new Date(date).toLocaleString(undefined, { timeZone: plan?.timezone, weekday: 'short', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' }) : heatmapLoading ? 'Loading corridor forecast…' : 'Forecast unavailable';
  return <>
    <MapView plan={plan} heatmap={heatmap} hourIndex={hour} showWeather={weatherVisible} selectedRouteId={selectedRouteId} onSelectRoute={onSelectRoute} />
    <div className="map-heading">
      <div className="map-heading-label"><span className="status-dot" />{plan ? 'JOURNEY OVERVIEW' : 'WEATHER-AWARE PLANNING'}</div>
      <h2>{plan && trip ? `${trip.origin.label.split(',')[0]} → ${trip.destination.label.split(',')[0]}` : 'The road ahead, in perspective.'}</h2>
      <p>{route ? `${Math.round(route.distance_mi).toLocaleString()} miles · ${formatDuration(route.duration_s)} · ${route.checkpoints.length} weather checkpoints` : 'Explore your route. Understand the conditions.'}</p>
    </div>
    {loading && <div className="map-loading-overlay" role="status"><span className="spinner" />Calculating weather along your journey…</div>}
    <div className="map-bottom">
      {plan && <section className="forecast-panel" aria-label="Corridor weather forecast">
        <div className="forecast-top"><span className="eyebrow">CORRIDOR FORECAST</span><label className="weather-toggle"><input type="checkbox" checked={weatherVisible} onChange={e => setWeatherVisible(e.target.checked)} />Weather layer</label></div>
        <div className="forecast-controls"><button type="button" className="forecast-play" disabled={!heatmap} aria-label={playing ? 'Pause forecast' : 'Play forecast'} onClick={() => setPlaying(p => !p)}>{playing ? 'Ⅱ' : '▶'}</button>
          <HeatmapSlider hourIndex={hour} maxHour={48} label={label} onChange={h => { setHour(h); setPlaying(false); }} disabled={!heatmap} />
        </div>
        <div className="forecast-ticks"><span>Departure</span><span>+12h</span><span>+24h</span><span>+36h</span><span>+48h</span></div>
        <p className="forecast-note">{heatmap ? `~${heatmap.cell_mi.toFixed(0)} mi cells · ` : ''}Map weather changes with time. Checkpoints use arrival forecasts.</p>
        {heatmapWarning && <p className="forecast-warning" role="status">{heatmapWarning}</p>}
      </section>}
      <div className="map-legend"><span className="eyebrow">WEATHER RISK</span><Legend /></div>
    </div>
  </>;
}
