import type { MapPanelKey } from '../map/panelVisibility';
import { MAP_PANEL_TOGGLES } from '../map/panelVisibility';

interface MapOverlayControlsProps {
  panels: Record<MapPanelKey, boolean>;
  onToggle: (key: MapPanelKey) => void;
}

/** Lives in the sidebar so overlay toggles never cover the map. */
export function MapOverlayControls({ panels, onToggle }: MapOverlayControlsProps) {
  return (
    <section className="overlay-controls" aria-label="Map overlays">
      <div className="section-heading">
        <h2 className="overlay-controls__title">Map overlays</h2>
        <span className="step-label">03 / View</span>
      </div>
      <p className="overlay-controls__hint">
        Show or hide cards on the map. Closing a card with × turns that toggle off here.
      </p>
      <div className="overlay-controls__toggles" role="group" aria-label="Toggle map panels">
        {MAP_PANEL_TOGGLES.map(({ key, label, short }) => (
          <button
            key={key}
            type="button"
            className={`overlay-toggle${panels[key] ? ' overlay-toggle--on' : ''}`}
            aria-pressed={panels[key]}
            title={label}
            onClick={() => onToggle(key)}
          >
            <span className="overlay-toggle__name">{short}</span>
            <span className="overlay-toggle__state">{panels[key] ? 'On' : 'Off'}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
