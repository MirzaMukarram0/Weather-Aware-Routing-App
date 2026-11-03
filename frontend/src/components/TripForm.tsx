import { useState } from 'react';
import type { LocationItem } from '../types/plan';
import { resolveLocationQuery } from '../api/client';
import { LocationField } from './LocationField';

export interface TripFormValues {
  origin: LocationItem; destination: LocationItem; departureLocal: string;
  loadLb: number; intervalMi: 10 | 25 | 50;
}
export function TripForm({ loading, onSubmit }: { loading: boolean; onSubmit: (values: TripFormValues) => void }) {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [originQ, setOriginQ] = useState('Chicago, IL');
  const [destQ, setDestQ] = useState('Denver, CO');
  const [origin, setOrigin] = useState<LocationItem | null>(null);
  const [destination, setDestination] = useState<LocationItem | null>(null);
  const [departureLocal, setDeparture] = useState(() => {
    const date = new Date(Date.now() + 3600000);
    return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  });
  const [load, setLoad] = useState('25000');
  const [intervalMi, setInterval] = useState<10 | 25 | 50>(25);
  const [error, setError] = useState('');
  const [resolving, setResolving] = useState(false);
  const busy = loading || resolving;
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError('');
    const weight = Number(load);
    if (!Number.isFinite(weight) || weight < 1 || weight > 80000) { setError('Enter a load between 1 and 80,000 lb.'); return; }
    setResolving(true);
    try {
      const start = await resolveLocationQuery(originQ, origin);
      const end = await resolveLocationQuery(destQ, destination);
      if (!start || !end) { setError('Search for a city and state, then choose a location.'); return; }
      setOrigin(start); setDestination(end); setOriginQ(start.label); setDestQ(end.label);
      onSubmit({ origin: start, destination: end, departureLocal, loadLb: weight, intervalMi });
    } catch (err) { setError((err as Error).message); }
    finally { setResolving(false); }
  }
  return <form className="trip-form" onSubmit={e => void submit(e)}>
    <div className="journey-fields">
      <LocationField id="origin" label="Origin" query={originQ} selected={origin} disabled={busy} onQueryChange={setOriginQ} onSelect={setOrigin} />
      <LocationField id="dest" label="Destination" query={destQ} selected={destination} disabled={busy} onQueryChange={setDestQ} onSelect={setDestination} />
    </div>
    <div className="field"><label htmlFor="departure">Departure <span className="field-indicator">{tz.replaceAll('_', ' ')}</span></label>
      <input id="departure" className="input" type="datetime-local" required value={departureLocal} disabled={busy} onChange={e => setDeparture(e.target.value)} />
    </div>
    <div className="field-row">
      <div className="field"><label htmlFor="load">Load weight <span className="field-indicator">lb</span></label>
        <input id="load" className="input" type="number" min="1" max="80000" step="1" required value={load} disabled={busy} onChange={e => setLoad(e.target.value)} />
      </div>
      <div className="field"><label htmlFor="interval">Sample every</label>
        <select id="interval" className="input" value={intervalMi} disabled={busy} onChange={e => setInterval(Number(e.target.value) as 10 | 25 | 50)}>
          <option value={10}>10 miles</option><option value={25}>25 miles</option><option value={50}>50 miles</option>
        </select>
      </div>
    </div>
    {error && <p className="banner banner--error" role="alert">{error}</p>}
    <button type="submit" className="btn btn--primary" disabled={busy}>
      {busy ? <><span className="spinner" />{loading ? 'Comparing routes…' : 'Finding locations…'}</> : <>Compare routes <span aria-hidden="true">↗</span></>}
    </button>
    <p className="form-note">Weather at your arrival time. Load adjusts wind risk.</p>
  </form>;
}
