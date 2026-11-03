import { useEffect, useState } from "react";
import type { LocationItem } from "../types/plan";
import { searchLocations } from "../api/client";

export interface TripFormValues {
  origin: LocationItem;
  destination: LocationItem;
  departureLocal: string;
  loadLb: number;
  intervalMi: 10 | 25 | 50;
}

interface TripFormProps {
  loading: boolean;
  onSubmit: (values: TripFormValues) => void;
}

export function TripForm({ loading, onSubmit }: TripFormProps) {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const defaultDep = new Date(Date.now() + 3600_000);
  const depLocal = defaultDep.toISOString().slice(0, 16);

  const [originQ, setOriginQ] = useState("Chicago, IL");
  const [destQ, setDestQ] = useState("Denver, CO");
  const [origin, setOrigin] = useState<LocationItem | null>(null);
  const [destination, setDestination] = useState<LocationItem | null>(null);
  const [departureLocal, setDepartureLocal] = useState(depLocal);
  const [loadLb, setLoadLb] = useState(25000);
  const [intervalMi, setIntervalMi] = useState<10 | 25 | 50>(25);

  useEffect(() => {
    const ac = new AbortController();
    void (async () => {
      try {
        const o = await searchLocations(originQ, ac.signal);
        if (o.items[0]) setOrigin(o.items[0]);
        const d = await searchLocations(destQ, ac.signal);
        if (d.items[0]) setDestination(d.items[0]);
      } catch {
        /* user will see validation on submit */
      }
    })();
    return () => ac.abort();
  }, [originQ, destQ]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!origin || !destination) return;
    onSubmit({ origin, destination, departureLocal, loadLb, intervalMi });
  };

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <h1>Weather-aware truck routing</h1>
      <p className="muted">Timezone: {tz}</p>
      <label>
        Origin
        <input value={originQ} onChange={(e) => setOriginQ(e.target.value)} />
      </label>
      <label>
        Destination
        <input value={destQ} onChange={(e) => setDestQ(e.target.value)} />
      </label>
      <button
        type="button"
        className="secondary"
        onClick={async () => {
          const o = await searchLocations(originQ);
          const d = await searchLocations(destQ);
          if (o.items[0]) setOrigin(o.items[0]);
          if (d.items[0]) setDestination(d.items[0]);
        }}
      >
        Resolve locations
      </button>
      <label>
        Departure (local)
        <input
          type="datetime-local"
          value={departureLocal}
          onChange={(e) => setDepartureLocal(e.target.value)}
        />
      </label>
      <label>
        Load (lb)
        <input
          type="number"
          min={1}
          max={80000}
          value={loadLb}
          onChange={(e) => setLoadLb(Number(e.target.value))}
        />
      </label>
      <label>
        Sample every
        <select
          value={intervalMi}
          onChange={(e) => setIntervalMi(Number(e.target.value) as 10 | 25 | 50)}
        >
          <option value={10}>10 mi</option>
          <option value={25}>25 mi</option>
          <option value={50}>50 mi</option>
        </select>
      </label>
      <button type="submit" disabled={loading || !origin || !destination}>
        {loading ? "Planning…" : "Plan routes"}
      </button>
    </form>
  );
}
