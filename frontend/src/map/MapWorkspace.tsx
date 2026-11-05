import { useEffect, useState } from 'react';
import type { HeatmapResponse, PlanResponse } from '../types/plan';
import type { TripFormValues } from '../components/TripForm';
import type { MapPanelKey } from './panelVisibility';
import { MapView } from './MapView';
import { Legend } from '../components/Legend';
import { HeatmapSlider } from '../components/HeatmapSlider';
import { formatDuration } from './utils';

interface Props {
  plan: PlanResponse | null;
  trip: TripFormValues | null;
  heatmap: HeatmapResponse | null;
  selectedRouteId: string | null;
  onSelectRoute: (id: string) => void;
  loading: boolean;
  heatmapLoading: boolean;
  heatmapWarning: string | null;
  panels: Record<MapPanelKey, boolean>;
  onTogglePanel: (key: MapPanelKey) => void;
}

function PanelClose({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="map-panel__close" aria-label={`Hide ${label}`} onClick={onClick}>
      ×
    </button>
  );
}

export function MapWorkspace(props: Props) {
  const {
    plan,
    trip,
    heatmap,
    selectedRouteId,
    onSelectRoute,
    loading,
    heatmapLoading,
    heatmapWarning,
    panels,
    onTogglePanel,
  } = props;
  const [hour, setHour] = useState(0);
  const [weatherVisible, setWeatherVisible] = useState(true);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing || !heatmap) return;
    const timer = window.setInterval(() => setHour((h) => (h >= 48 ? 0 : h + 1)), 900);
    return () => window.clearInterval(timer);
  }, [playing, heatmap]);

  const route = plan?.routes.find((r) => r.id === selectedRouteId);
  const date = heatmap?.timestamps_utc[hour];
  const label = date
    ? new Date(date).toLocaleString(undefined, {
        timeZone: plan?.timezone,
        weekday: 'short',
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      })
    : heatmapLoading
      ? 'Loading corridor forecast…'
      : 'Forecast unavailable';

  return (
    <>
      <MapView
        plan={plan}
        heatmap={heatmap}
        hourIndex={hour}
        showWeather={weatherVisible}
        showPreview={panels.preview}
        selectedRouteId={selectedRouteId}
        onSelectRoute={onSelectRoute}
        onHidePreview={() => onTogglePanel('preview')}
      />

      {panels.overview && (
        <div className="map-heading map-panel">
          <PanelClose label="trip summary" onClick={() => onTogglePanel('overview')} />
          <div className="map-heading-label">
            <span className="status-dot" />
            {plan ? 'JOURNEY OVERVIEW' : 'WEATHER-AWARE PLANNING'}
          </div>
          <h2>
            {plan && trip
              ? `${trip.origin.label.split(',')[0]} → ${trip.destination.label.split(',')[0]}`
              : 'The road ahead, in perspective.'}
          </h2>
          <p>
            {route
              ? `${Math.round(route.distance_mi).toLocaleString()} miles · ${formatDuration(route.duration_s)} · ${route.checkpoints.length} weather checkpoints`
              : 'Explore your route. Understand the conditions.'}
          </p>
        </div>
      )}

      {loading && (
        <div className="map-loading-overlay" role="status">
          <span className="spinner" />
          Calculating weather along your journey…
        </div>
      )}

      <div className="map-bottom">
        {plan && panels.forecast && (
          <section className="forecast-panel map-panel" aria-label="Corridor weather forecast">
            <PanelClose label="corridor forecast" onClick={() => onTogglePanel('forecast')} />
            <div className="forecast-top">
              <span className="eyebrow">CORRIDOR FORECAST</span>
              <label className="weather-toggle">
                <input
                  type="checkbox"
                  checked={weatherVisible}
                  onChange={(e) => setWeatherVisible(e.target.checked)}
                />
                Weather layer
              </label>
            </div>
            <div className="forecast-controls">
              <button
                type="button"
                className="forecast-play"
                disabled={!heatmap}
                aria-label={playing ? 'Pause forecast' : 'Play forecast'}
                onClick={() => setPlaying((p) => !p)}
              >
                {playing ? 'Ⅱ' : '▶'}
              </button>
              <HeatmapSlider
                hourIndex={hour}
                maxHour={48}
                label={label}
                onChange={(h) => {
                  setHour(h);
                  setPlaying(false);
                }}
                disabled={!heatmap}
              />
            </div>
            <div className="forecast-ticks">
              <span>Departure</span>
              <span>+12h</span>
              <span>+24h</span>
              <span>+36h</span>
              <span>+48h</span>
            </div>
            <p className="forecast-note">
              {heatmap ? `~${heatmap.cell_mi.toFixed(0)} mi cells · ` : ''}
              Map weather changes with time. Checkpoints use arrival forecasts.
            </p>
            {heatmapWarning && (
              <p className="forecast-warning" role="status">
                {heatmapWarning}
              </p>
            )}
          </section>
        )}
        {panels.legend && (
          <div className="map-legend map-panel">
            <PanelClose label="weather risk legend" onClick={() => onTogglePanel('legend')} />
            <span className="eyebrow">WEATHER RISK</span>
            <Legend />
          </div>
        )}
      </div>
    </>
  );
}
