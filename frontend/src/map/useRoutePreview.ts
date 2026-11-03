import { useEffect, useMemo, useState } from 'react';
import { decodePolyline } from './utils';
import type { RoutePlan } from '../types/plan';

export function useRoutePreview(route: RoutePlan | undefined) {
  const reducedMotion = useMemo(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches, []);
  const [progress, setProgress] = useState(0);
  const [playing, setPlaying] = useState(false);
  const path = useMemo(() => route ? decodePolyline(route.polyline).map(([lat, lon]) => [lon, lat] as [number, number]) : [], [route]);
  const cumulative = useMemo(() => {
    const distances = [0];
    for (let i = 1; i < path.length; i++) {
      const latitude = (path[i][1] + path[i - 1][1]) * Math.PI / 360;
      distances.push(distances[i - 1] + Math.hypot((path[i][0] - path[i - 1][0]) * Math.cos(latitude), path[i][1] - path[i - 1][1]));
    }
    return distances;
  }, [path]);
  useEffect(() => { setProgress(0); setPlaying(!!route && !reducedMotion); }, [route, reducedMotion]);
  useEffect(() => {
    if (!playing) return;
    let frame = 0; let previous = 0;
    const step = (now: number) => {
      if (previous && now - previous < 32) { frame = requestAnimationFrame(step); return; }
      const elapsed = previous ? Math.min(now - previous, 100) : 0; previous = now;
      if (!document.hidden) setProgress(p => Math.min(1, p + elapsed / 14000));
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [playing]);
  useEffect(() => { if (progress >= 1) setPlaying(false); }, [progress]);
  const target = (cumulative.at(-1) ?? 0) * progress;
  let index = cumulative.findIndex(d => d >= target);
  if (index < 1) index = 1;
  const a = path[index - 1] ?? [0, 0]; const b = path[index] ?? a;
  const span = (cumulative[index] ?? 0) - (cumulative[index - 1] ?? 0);
  const fraction = span > 0 ? (target - cumulative[index - 1]) / span : 0;
  const point: [number, number] = [a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction];
  const angle = -Math.atan2((b[0] - a[0]) * Math.cos(a[1] * Math.PI / 180), b[1] - a[1]) * 180 / Math.PI;
  return { point, angle, progress, playing, reducedMotion, toggle: () => {
    if (progress >= 1) setProgress(0);
    setPlaying(p => !p);
  }, replay: () => { setProgress(0); setPlaying(true); } };
}
