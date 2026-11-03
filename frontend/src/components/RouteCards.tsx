import type { PlanResponse } from "../types/plan";
import { formatDuration } from "../map/utils";

interface RouteCardsProps {
  plan: PlanResponse;
  selectedRouteId: string | null;
  onSelect: (id: string) => void;
}

export function RouteCards({ plan, selectedRouteId, onSelect }: RouteCardsProps) {
  return (
    <div className="route-cards">
      {plan.warnings.map((w) => (
        <p key={w} className="banner warn">
          {w}
        </p>
      ))}
      {plan.routes.map((route) => {
        const rec = route.id === plan.recommendation.route_id;
        return (
          <button
            type="button"
            key={route.id}
            className={`route-card ${selectedRouteId === route.id ? "selected" : ""}`}
            onClick={() => onSelect(route.id)}
          >
            {rec && <span className="badge">Recommended</span>}
            <strong>{route.id}</strong>
            <div>
              {route.distance_mi} mi · {formatDuration(route.duration_s)}
            </div>
            <div className="stats">
              Severe {route.summary.severe_mi} mi · High {route.summary.high_mi} mi · No-travel{" "}
              {route.summary.no_travel_mi} mi
            </div>
            {rec && (
              <p className="reason">
                Because: {plan.recommendation.reason}
                {plan.recommendation.warnings.map((w) => (
                  <span key={w} className="banner warn inline">
                    {w}
                  </span>
                ))}
              </p>
            )}
          </button>
        );
      })}
    </div>
  );
}
