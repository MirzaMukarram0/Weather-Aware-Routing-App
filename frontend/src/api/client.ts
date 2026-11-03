const base = import.meta.env.VITE_API_URL ?? "http://localhost:8080";

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
    throw new Error(body.error ?? `Request failed (${res.status})`);
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
