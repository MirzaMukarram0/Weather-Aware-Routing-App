export type MapPanelKey = 'overview' | 'preview' | 'forecast' | 'legend';

export const MAP_PANEL_TOGGLES: { key: MapPanelKey; label: string; short: string }[] = [
  { key: 'overview', label: 'Trip summary', short: 'Summary' },
  { key: 'preview', label: 'Route preview animation', short: 'Preview' },
  { key: 'forecast', label: 'Corridor forecast controls', short: 'Forecast' },
  { key: 'legend', label: 'Weather risk legend', short: 'Legend' },
];

export const DEFAULT_MAP_PANELS: Record<MapPanelKey, boolean> = {
  overview: true,
  preview: false,
  forecast: true,
  legend: true,
};
