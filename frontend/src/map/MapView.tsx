import { useEffect, useMemo, useRef, useState } from 'react';
import { FlyToInterpolator, WebMercatorViewport } from '@deck.gl/core';
import type { MapViewState, PickingInfo } from '@deck.gl/core';
import DeckGL from '@deck.gl/react';
import Map from 'react-map-gl/maplibre';
import { PathLayer, ScatterplotLayer, PolygonLayer, IconLayer, TextLayer } from '@deck.gl/layers';
import type { Checkpoint, HeatmapCell, HeatmapResponse, PlanResponse } from '../types/plan';
import { LEVEL_COLORS, decodePolyline, formatDuration } from './utils';
import { useRoutePreview } from './useRoutePreview';

const US_VIEW: MapViewState = { longitude: -97, latitude: 38.5, zoom: 3.6, pitch: 0, bearing: 0 };
const ARROW = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><circle cx="24" cy="24" r="22" fill="white"/><circle cx="24" cy="24" r="18" fill="#126b68"/><path d="M24 10L35 34L24 29L13 34Z" fill="white"/></svg>')}`;

interface Props {
  plan: PlanResponse | null;
  heatmap: HeatmapResponse | null;
  hourIndex: number;
  showWeather: boolean;
  showPreview: boolean;
  selectedRouteId: string | null;
  onSelectRoute: (id: string) => void;
  onHidePreview?: () => void;
}
export function MapView({
  plan,
  heatmap,
  hourIndex,
  showWeather,
  showPreview,
  selectedRouteId,
  onSelectRoute,
  onHidePreview,
}: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [view, setView] = useState<MapViewState>(US_VIEW);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; cp: Checkpoint } | null>(null);
  const [mapError, setMapError] = useState(false);
  const route = plan?.routes.find(r => r.id === selectedRouteId);
  const preview = useRoutePreview(route);
  const paths = useMemo(() => plan?.routes.map(r => ({ route: r, path: decodePolyline(r.polyline).map(([lat, lon]) => [lon, lat] as [number, number]) })) ?? [], [plan]);
  const fitted = useMemo(() => {
    const points = paths.flatMap(p => p.path);
    if (!points.length) return US_VIEW;
    const lons = points.map(p => p[0]); const lats = points.map(p => p[1]);
    const bounds: [[number, number], [number, number]] = [
      [Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)],
    ];
    const fittedView = new WebMercatorViewport(size).fitBounds(bounds, {
      padding: { top: 100, bottom: 140, left: 48, right: 48 },
      maxZoom: 10,
    });
    return { longitude: fittedView.longitude, latitude: fittedView.latitude, zoom: fittedView.zoom, pitch: 0, bearing: 0 };
  }, [paths, size]);
  const flyTo = (target: MapViewState) => setView({ ...target, transitionDuration: preview.reducedMotion ? 0 : 1200, transitionInterpolator: new FlyToInterpolator() });
  useEffect(() => {
    const observer = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      if (width && height) setSize({ width, height });
    });
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    setView({ ...fitted, transitionDuration: preview.reducedMotion ? 0 : 1200, transitionInterpolator: new FlyToInterpolator() });
  }, [fitted, preview.reducedMotion]);
  useEffect(() => { setTooltip(null); }, [selectedRouteId]);

  const weatherLayer = useMemo(() => new PolygonLayer<HeatmapCell>({
    id: 'weather', data: heatmap?.cells ?? [], visible: showWeather, opacity: 0.3,
    getPolygon: d => d.polygon.map(p => [p.lon, p.lat]), getFillColor: d => LEVEL_COLORS[d.levels_by_hour[hourIndex] ?? 'UNKNOWN'],
    updateTriggers: { getFillColor: hourIndex }, stroked: false,
  }), [heatmap, showWeather, hourIndex]);
  const routeLayers = useMemo(() => {
    const sorted = [...paths].sort((a, b) => Number(a.route.id === selectedRouteId) - Number(b.route.id === selectedRouteId));
    return sorted.flatMap(({ route: r, path }) => {
      const active = r.id === selectedRouteId;
      return [new PathLayer({ id: `${r.id}-outline`, data: [{ path }], getPath: d => d.path, getColor: [255, 255, 255, 230], getWidth: active ? 9 : 6, widthUnits: 'pixels' }),
        new PathLayer({ id: r.id, data: [{ path }], getPath: d => d.path, getColor: active ? [19, 107, 105, 255] : [100, 116, 139, 200],
          getWidth: active ? 5 : 3, widthUnits: 'pixels', pickable: true, onClick: () => onSelectRoute(r.id) })];
    });
  }, [paths, selectedRouteId, onSelectRoute]);
  const checkpointLayers = useMemo(() => {
    if (!route) return [];
    const showTip = (info: PickingInfo<Checkpoint>) => setTooltip(info.object ? { x: info.x, y: info.y, cp: info.object } : null);
    const endpoints = [route.checkpoints[0], route.checkpoints.at(-1)].filter((p): p is Checkpoint => !!p);
    return [new ScatterplotLayer<Checkpoint>({ id: 'checkpoints', data: route.checkpoints,
      getPosition: d => [d.lon, d.lat], getFillColor: d => LEVEL_COLORS[d.risk_level], getRadius: 4.5, radiusUnits: 'pixels',
      stroked: true, getLineColor: [255, 255, 255], getLineWidth: 1.5, lineWidthUnits: 'pixels', pickable: true, onHover: showTip, onClick: showTip }),
      new ScatterplotLayer<Checkpoint>({ id: 'endpoints', data: endpoints, getPosition: d => [d.lon, d.lat], getRadius: 11,
        radiusUnits: 'pixels', getFillColor: [20, 43, 54], stroked: true, getLineColor: [255, 255, 255], getLineWidth: 3, lineWidthUnits: 'pixels' }),
      new TextLayer<Checkpoint>({ id: 'endpoint-labels', data: endpoints, getPosition: d => [d.lon, d.lat], getText: (_, { index }) => index === 0 ? 'A' : 'B',
        getSize: 11, getColor: [255, 255, 255], fontFamily: 'Arial', fontWeight: 'bold' })];
  }, [route]);
  const vehicle = new IconLayer({
    id: 'route-preview',
    data: route && showPreview ? [{ position: preview.point }] : [],
    getPosition: d => d.position, getIcon: () => ({ url: ARROW, width: 48, height: 48, anchorY: 24 }),
    getSize: 36, getAngle: preview.angle, updateTriggers: { getAngle: preview.angle }, billboard: true,
  });
  const value = (v: number | null, unit: string) => v === null ? 'Unavailable' : `${v.toFixed(2).replace(/\.00$/, '')} ${unit}`;
  return <div className="map-wrap" ref={container}>
    <DeckGL viewState={view} onViewStateChange={({ viewState }) => setView(viewState as MapViewState)} controller
      layers={[weatherLayer, ...routeLayers, ...checkpointLayers, vehicle]} getCursor={({ isHovering }) => isHovering ? 'pointer' : 'grab'}>
      <Map mapStyle="https://tiles.openfreemap.org/styles/liberty" attributionControl={false} onError={() => setMapError(true)} />
      <p className="map-attrib">
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
          © OSM
        </a>
        {' · '}
        <a href="https://maplibre.org/" target="_blank" rel="noreferrer">
          MapLibre
        </a>
      </p>
    </DeckGL>
    <div className="map-controls" aria-label="Map controls">
      <button type="button" aria-label="Zoom in" onClick={() => setView(v => ({ ...v, zoom: Math.min(18, v.zoom + 1) }))}>+</button>
      <button type="button" aria-label="Zoom out" onClick={() => setView(v => ({ ...v, zoom: Math.max(1, v.zoom - 1) }))}>−</button>
      <button type="button" aria-label="Fit all routes" title="Fit all routes" onClick={() => flyTo(fitted)}>⌖</button>
    </div>
    {mapError && <p className="map-error" role="status">Some map tiles could not load. Route results remain available.</p>}
    {route && showPreview && (
      <div className="preview-controls map-panel">
        {onHidePreview && (
          <button type="button" className="map-panel__close" aria-label="Hide route preview" onClick={onHidePreview}>
            ×
          </button>
        )}
        <button type="button" onClick={preview.toggle} aria-label={preview.playing ? 'Pause route preview' : 'Play route preview'}>
          {preview.playing ? 'Ⅱ' : '▶'}
        </button>
        <div>
          <strong>
            Route preview <span>{Math.round(preview.progress * 100)}%</span>
          </strong>
          <small>Illustration · not live navigation</small>
          <div className="preview-progress">
            <span style={{ width: `${preview.progress * 100}%` }} />
          </div>
        </div>
        <button type="button" onClick={preview.replay} aria-label="Replay route preview">
          ↻
        </button>
      </div>
    )}
    {tooltip && plan && <div className="checkpoint-tooltip" role="status" style={{ left: Math.min(size.width - 260, Math.max(12, tooltip.x + 14)), top: Math.max(12, Math.min(size.height - 260, tooltip.y - 60)) }}>
      <div className="tooltip-title"><strong>Mile {tooltip.cp.distance_mi.toFixed(1)}</strong><span>{tooltip.cp.risk_level.replace('_', ' ')}</span></div>
      <p>{new Date(tooltip.cp.eta_utc).toLocaleString(undefined, { timeZone: plan.timezone, month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })}</p>
      <small>{formatDuration((Date.parse(tooltip.cp.eta_utc) - Date.parse(plan.departure_utc)) / 1000)} after departure</small>
      <dl><dt>Wind / gust</dt><dd>{value(tooltip.cp.weather.wind_sustained_mph, '')} / {value(tooltip.cp.weather.wind_gust_mph, 'mph')}</dd>
        <dt>Rain</dt><dd>{value(tooltip.cp.weather.rain_in_hr, 'in/hr')}</dd><dt>Snow</dt><dd>{value(tooltip.cp.weather.snow_in_hr, 'in/hr')}</dd></dl>
      {!tooltip.cp.weather_complete && <small>Incomplete weather coverage</small>}
    </div>}
  </div>;
}
