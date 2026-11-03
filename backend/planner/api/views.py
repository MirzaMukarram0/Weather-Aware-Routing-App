from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from planner.api.heatmap_build import build_heatmap
from planner.api.plan_build import build_plan
from planner.api.serializers import (
    HeatmapRequestSerializer,
    LocationQuerySerializer,
    PlanRequestSerializer,
)
from planner.providers.errors import ProviderError
from planner.providers.nominatim import autosuggest


def _error(message: str, code: int = 502) -> Response:
    return Response({"error": message}, status=code)


@api_view(["GET"])
def health(_request: Request) -> Response:
    return Response({"status": "ok"})


@api_view(["GET"])
def locations(request: Request) -> Response:
    ser = LocationQuerySerializer(data=request.query_params)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        items = autosuggest(ser.validated_data["q"])
    except ProviderError as e:
        return _error(str(e), e.status)
    return Response({"items": items})


@api_view(["POST"])
def plan(request: Request) -> Response:
    ser = PlanRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    data = ser.validated_data
    try:
        payload = build_plan(
            origin=(data["origin_lat"], data["origin_lon"]),
            dest=(data["dest_lat"], data["dest_lon"]),
            departure=data["departure"],
            timezone=data["timezone"],
            load_lb=data["load_lb"],
            interval_mi=int(data["interval_mi"]),
        )
    except ProviderError as e:
        return _error(str(e), e.status)
    return Response(payload)


@api_view(["POST"])
def heatmap(request: Request) -> Response:
    ser = HeatmapRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    data = ser.validated_data
    polylines = [r.get("polyline", "") for r in data["routes"] if r.get("polyline")]
    try:
        payload = build_heatmap(polylines, data["departure"], data["load_lb"])
    except ValueError:
        return Response({"error": "No route geometries"}, status=400)
    return Response(payload)
