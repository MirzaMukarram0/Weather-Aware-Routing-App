import { useMemo, useState } from "react";
import type { MapViewState } from "@deck.gl/core";
import DeckGL from "@deck.gl/react";
import Map, { NavigationControl } from "react-map-gl";
import maplibregl from "maplibre-gl";
import { PathLayer, ScatterplotLayer, PolygonLayer } from "@deck.gl/layers";
import type { HeatmapCell, HeatmapResponse, PlanResponse, RiskLevel } from "../types/plan";
import { LEVEL_COLORS, decodePolyline } from "./utils";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

interface MapViewProps {
  plan: PlanResponse | null;
  heatmap: HeatmapResponse | null;
  hourIndex: number;
  selectedRouteId: string | null;
  onSelectRoute: (id: string) => void;
}

export function MapView({
  plan,
  heatmap,
  hourIndex,
  selectedRouteId,
  onSelectRoute,
}: MapViewProps) {
  const [viewState, setViewState] = useState({
    longitude: -98,
    latitude: 39,
    zoom: 4,
    pitch: 0,
    bearing: 0,
  });

  const layers = useMemo(() => {
    const out = [];
    if (heatmap) {
      out.push(
        new PolygonLayer<HeatmapCell>({
          id: "heatmap-cells",
          data: heatmap.cells,
          getPolygon: (d) => d.polygon.map((p: { lat: number; lon: number }) => [p.lon, p.lat]),
          getFillColor: (d) =>
            LEVEL_COLORS[(d.levels_by_hour[hourIndex] ?? "UNKNOWN") as RiskLevel],
          updateTriggers: { getFillColor: hourIndex },
          stroked: false,
        }),
      );
    }
    if (plan) {
      plan.routes.forEach((route, idx) => {
        const path = decodePolyline(route.polyline).map(
          ([lat, lon]) => [lon, lat] as [number, number],
        );
        const selected = route.id === selectedRouteId;
        const recommended = route.id === plan.recommendation.route_id;
        out.push(
          new PathLayer({
            id: `route-${idx}`,
            data: [{ path }],
            getPath: (d: { path: [number, number][] }) => d.path,
            getColor: selected
              ? [37, 99, 235, 255]
              : recommended
                ? [16, 185, 129, 220]
                : [100, 116, 139, 180],
            getWidth: selected ? 8 : recommended ? 6 : 3,
            widthUnits: "pixels",
            pickable: true,
            onClick: () => onSelectRoute(route.id),
          }),
        );
      });
      const route = plan.routes.find((r) => r.id === selectedRouteId);
      if (route) {
        out.push(
          new ScatterplotLayer({
            id: "checkpoints",
            data: route.checkpoints,
            getPosition: (d) => [d.lon, d.lat],
            getFillColor: (d) => LEVEL_COLORS[d.risk_level as RiskLevel],
            getRadius: 6,
            radiusUnits: "pixels",
          }),
        );
      }
    }
    return out;
  }, [plan, heatmap, hourIndex, selectedRouteId, onSelectRoute]);

  return (
    <div className="map-wrap">
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) => {
          const v = vs as MapViewState;
          setViewState({
            longitude: v.longitude,
            latitude: v.latitude,
            zoom: v.zoom,
            pitch: v.pitch ?? 0,
            bearing: v.bearing ?? 0,
          });
        }}
        controller
        layers={layers}
      >
        <Map
          {...viewState}
          onMove={(e) => setViewState(e.viewState)}
          mapStyle={MAP_STYLE}
          // react-map-gl v7 MapLib typing targets mapbox-gl; runtime works with maplibre-gl
          mapLib={maplibregl as never}
        >
          <NavigationControl position="top-right" />
        </Map>
      </DeckGL>
    </div>
  );
}
