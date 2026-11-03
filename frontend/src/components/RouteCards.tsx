import { memo } from 'react';
import type { PlanResponse, RiskLevel, RouteSummary } from '../types/plan';
import { formatDuration, LEVEL_COLORS } from '../map/utils';

const bands: { label: string; level: RiskLevel; field: keyof RouteSummary }[] = [
  { label: 'Low', level: 'LOW', field: 'low_mi' }, { label: 'Moderate', level: 'MODERATE', field: 'moderate_mi' },
  { label: 'High', level: 'HIGH', field: 'high_mi' }, { label: 'Severe', level: 'SEVERE', field: 'severe_mi' },
  { label: 'No travel', level: 'NO_TRAVEL', field: 'no_travel_mi' }, { label: 'Unknown', level: 'UNKNOWN', field: 'unknown_mi' },
];
export const RouteCards = memo(function RouteCards({ plan, selectedRouteId, onSelect }: {
  plan: PlanResponse; selectedRouteId: string | null; onSelect: (id: string) => void;
}) {
  return <div className="route-list">
    {[...plan.routes].sort((a, b) => a.rank - b.rank).map(route => {
      const recommended = route.id === plan.recommendation.route_id;
      const selected = route.id === selectedRouteId;
      const number = Number(route.id.replace('route-', '')) + 1;
      const s = route.summary;
      return <button key={route.id} type="button" className={`route-card ${selected ? 'route-card--selected' : ''}`}
        aria-pressed={selected} onClick={() => onSelect(route.id)}>
        <div className="route-card__head"><span className="route-title"><span className="route-number">{number}</span>Route {number}</span>
          {recommended ? <span className="pill">Recommended</span> : <span className="muted">Alternative</span>}
        </div>
        <div className="route-stats"><strong>{formatDuration(route.duration_s)}</strong><span>{Math.round(route.distance_mi).toLocaleString()} miles</span></div>
        <div className="risk-bar" aria-hidden="true">{bands.map(b => <span key={b.level} style={{ flexGrow: Number(s[b.field]), background: `rgb(${LEVEL_COLORS[b.level].slice(0, 3).join(',')})` }} />)}</div>
        <div className="risk-miles">{bands.filter(b => Number(s[b.field]) > 0).map(b => <span key={b.level}>
          <i style={{ background: `rgb(${LEVEL_COLORS[b.level].slice(0, 3).join(',')})` }} />{b.label} <b>{Number(s[b.field]).toFixed(1)} mi</b>
        </span>)}</div>
        <div className="route-card__foot"><span>Avg risk <b>{s.avg_risk === null ? '—' : `${s.avg_risk.toFixed(2)} / 4`}</b></span>
          <span>{s.weather_complete ? 'Complete forecast' : 'Incomplete forecast'}</span></div>
        {s.no_travel_mi > 0 && <p className="route-danger">No travel on {s.no_travel_mi.toFixed(1)} miles</p>}
        {selected && <p className="route-reason">{route.comparison_reason}</p>}
      </button>;
    })}
  </div>;
});
