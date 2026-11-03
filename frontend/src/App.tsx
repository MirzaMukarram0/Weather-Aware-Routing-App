import { Suspense, lazy } from 'react';
import { TripForm } from './components/TripForm';
import { RouteCards } from './components/RouteCards';
import { useTripPlan } from './hooks/useTripPlan';
import './index.css';

const MapWorkspace = lazy(() => import('./map/MapWorkspace').then(m => ({ default: m.MapWorkspace })));

export default function App() {
  const state = useTripPlan();
  const { plan, trip, loading, error } = state;
  return <div className="app-shell">
    <header className="app-header">
      <a className="brand" href="/" aria-label="Weather-aware routing home"><span className="brand-mark" aria-hidden="true">↗</span>
        <span>Weather<span className="brand-light">Aware</span><small>ROUTE INTELLIGENCE</small></span></a>
      <div className="header-context"><span className="status-dot" />Plan with the forecast ahead</div>
      <span className="header-tag">US route planner</span>
    </header>
    <aside className="control-panel">
      <div className="panel-scroll">
        <div className="section-heading"><span className="eyebrow">YOUR JOURNEY</span><span className="step-label">01 / Plan</span></div>
        <h1>A better way forward.</h1><p className="intro">Compare the weather along every route.</p>
        <details className="trip-details" open={!plan}>
          <summary><span>{trip ? `${trip.origin.label.split(',')[0]} → ${trip.destination.label.split(',')[0]}` : 'Trip details'}</span><span>Edit trip</span></summary>
          <TripForm loading={loading} onSubmit={state.planTrip} />
        </details>
        {loading && <div className="planning-status" role="status"><span className="spinner" /><div><strong>Looking down the road</strong><p>Finding alternatives and checking weather at each arrival time.</p></div></div>}
        {error && <p className="banner banner--error" role="alert">{error}</p>}
        {plan && <section className="results-section" aria-label="Route comparison">
          <div className="section-heading"><h2>{plan.routes.length} route{plan.routes.length === 1 ? '' : 's'} compared</h2><span className="step-label">02 / Choose</span></div>
          <div className={`recommendation ${plan.recommendation.warnings.length ? 'recommendation--warn' : ''}`} role="status">
            <span className="recommendation-icon" aria-hidden="true">{plan.recommendation.warnings.length ? '!' : '✓'}</span><div>
              <strong>{plan.recommendation.warnings.length ? 'Best ranked · caution required' : 'Your recommended route'}</strong>
              <p>{plan.recommendation.reason.charAt(0).toUpperCase() + plan.recommendation.reason.slice(1)}.</p>
              {plan.recommendation.warnings.map(w => <p key={w}>{w}</p>)}
            </div>
          </div>
          <RouteCards plan={plan} selectedRouteId={state.selectedRouteId} onSelect={state.setSelectedRouteId} />
          {plan.warnings.map(w => <p className="inline-note" key={w}>{w}</p>)}
        </section>}
        {!plan && !loading && <div className="how-it-works"><span className="eyebrow">AHEAD OF THE WEATHER</span>
          <div><b>01</b><p><strong>Compare your options</strong>Up to three driving routes, side by side.</p></div>
          <div><b>02</b><p><strong>See what’s ahead</strong>Wind, rain and snow at your arrival time.</p></div>
          <div><b>03</b><p><strong>Choose with context</strong>A clear recommendation with risk explained.</p></div>
        </div>}
      </div>
      <footer className="panel-footer">Driving routes · truck restrictions not verified.<br /><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap</a><span> · </span><a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Weather by Open-Meteo</a></footer>
    </aside>
    <main className="map-stage" aria-label="Route and weather map">
      <Suspense fallback={<div className="map-loading"><span className="spinner" /> Loading your map…</div>}>
        <MapWorkspace key={plan?.departure_utc ?? 'empty'} plan={plan} trip={trip} heatmap={state.heatmap}
          selectedRouteId={state.selectedRouteId} onSelectRoute={state.setSelectedRouteId}
          loading={loading} heatmapLoading={state.heatmapLoading} heatmapWarning={state.heatmapWarning} />
      </Suspense>
    </main>
  </div>;
}
