import { useEffect, useRef, useState } from 'react';
import { searchLocations } from '../api/client';
import type { LocationItem } from '../types/plan';

interface Props {
  id: string; label: string; query: string; selected: LocationItem | null;
  disabled?: boolean; onQueryChange: (value: string) => void;
  onSelect: (value: LocationItem | null) => void;
}

export function LocationField({ id, label, query, selected, disabled, onQueryChange, onSelect }: Props) {
  const [items, setItems] = useState<LocationItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState('');
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function search() {
    controller.current?.abort();
    const ac = new AbortController(); controller.current = ac;
    setSearching(true); setMessage(''); setItems([]);
    try {
      const result = await searchLocations(query.trim(), ac.signal);
      if (ac.signal.aborted) return;
      setItems(result.items);
      if (!result.items.length) setMessage('No matches. Try a city and state.');
    } catch (error) {
      if (!ac.signal.aborted) setMessage((error as Error).message);
    } finally { if (!ac.signal.aborted) setSearching(false); }
  }
  return <div className="location-field">
    <label htmlFor={id}>{label}<span className="field-indicator">{selected ? '✓ Located' : 'City or address'}</span></label>
    <div className="location-input">
      <span className={`location-dot ${id === 'dest' ? 'location-dot--end' : ''}`} aria-hidden="true" />
      <input id={id} className="input" value={query} disabled={disabled} autoComplete="off"
        placeholder={id === 'origin' ? 'Where are you starting?' : 'Where are you heading?'}
        onChange={e => { controller.current?.abort(); setSearching(false); onQueryChange(e.target.value); onSelect(null); setItems([]); setMessage(''); }}
        onKeyDown={e => { if (e.key === 'Enter' && !selected) { e.preventDefault(); void search(); } if (e.key === 'Escape') setItems([]); }} />
      <button type="button" className="search-button" disabled={disabled || searching || query.trim().length < 2}
        aria-label={`Search ${label.toLowerCase()}`} onClick={() => void search()}>{searching ? '…' : 'Find'}</button>
    </div>
    {!!items.length && <ul className="location-results" aria-label={`${label} search results`}>
      {items.map(item => <li key={item.id}><button type="button" onClick={() => {
        onSelect(item); onQueryChange(item.label); setItems([]);
      }}>{item.label}</button></li>)}
    </ul>}
    {message && <p className="field-error" role="status">{message}</p>}
  </div>;
}
