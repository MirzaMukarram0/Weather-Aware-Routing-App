const base = import.meta.env.VITE_API_URL ?? "";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const details = Object.entries(body).map(([field, errors]) =>
      `${field.replaceAll('_', ' ')}: ${Array.isArray(errors) ? errors.join(' ') : String(errors)}`,
    ).join(' · ');
    throw new Error(typeof body.error === 'string' ? body.error : details || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function searchLocations(q: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ q });
  return apiFetch<{ items: import("../types/plan").LocationItem[] }>(
    `/api/locations?${params}`,
    { signal },
  );
}

export function postPlan(body: import("../types/plan").PlanRequest, signal?: AbortSignal) {
  return apiFetch<import("../types/plan").PlanResponse>("/api/plan", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}

export function postHeatmap(
  body: {
    departure: string;
    timezone: string;
    load_lb: number;
    routes: { polyline: string }[];
  },
  signal?: AbortSignal,
) {
  return apiFetch<import("../types/plan").HeatmapResponse>("/api/heatmap", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}

export function getHealth() {
  return apiFetch<{ status: string }>("/api/health");
}

const MIN_LOCATION_QUERY = 2;

/** Use explicit selection, or Nominatim top hit for free-text. */
export async function resolveLocationQuery(
  query: string,
  selected: import("../types/plan").LocationItem | null,
): Promise<import("../types/plan").LocationItem | null> {
  if (selected && selected.label === query.trim()) {
    return selected;
  }
  const trimmed = query.trim();
  if (trimmed.length < MIN_LOCATION_QUERY) {
    return null;
  }
  const res = await searchLocations(trimmed);
  return res.items[0] ?? null;
}
