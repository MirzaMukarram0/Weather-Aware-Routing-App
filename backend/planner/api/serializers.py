"""Validate public inputs before provider I/O or geometry processing."""

import math
import re
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import polyline
from django.utils import timezone
from rest_framework import serializers


class FiniteFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            self.fail("invalid")
        return value


class OffsetDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        if not isinstance(value, str) or not re.search(r"(Z|[+-]\d{2}:?\d{2})$", value):
            raise serializers.ValidationError("Include a timezone offset in the departure time.")
        return super().to_internal_value(value)


class LocationQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=200, allow_blank=False)


class TripTimeSerializer(serializers.Serializer):
    departure = OffsetDateTimeField()
    timezone = serializers.CharField(max_length=64)
    load_lb = FiniteFloatField(min_value=1, max_value=80000)

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise serializers.ValidationError("Choose a valid IANA timezone.") from exc
        return value

    def validate_departure(self, value):
        now = timezone.now()
        if value < now - timedelta(minutes=15) or value > now + timedelta(days=13):
            raise serializers.ValidationError("Departure must be now or within the next 13 days.")
        return value


class PlanRequestSerializer(TripTimeSerializer):
    origin_lat = FiniteFloatField(min_value=-85, max_value=85)
    origin_lon = FiniteFloatField(min_value=-180, max_value=180)
    origin_label = serializers.CharField(max_length=500, required=False, allow_blank=True)
    dest_lat = FiniteFloatField(min_value=-85, max_value=85)
    dest_lon = FiniteFloatField(min_value=-180, max_value=180)
    dest_label = serializers.CharField(max_length=500, required=False, allow_blank=True)
    interval_mi = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate(self, data):
        if (data["origin_lat"], data["origin_lon"]) == (data["dest_lat"], data["dest_lon"]):
            raise serializers.ValidationError("Choose different origin and destination locations.")
        return data


class RouteGeometrySerializer(serializers.Serializer):
    polyline = serializers.CharField(max_length=100000)

    def validate_polyline(self, value):
        try:
            if any(not 63 <= ord(char) <= 126 for char in value):
                raise ValueError
            points = polyline.decode(value, precision=5)
            if len(points) < 2 or any(
                not (-85 <= lat <= 85 and -180 <= lon <= 180) for lat, lon in points
            ):
                raise ValueError
        except (ValueError, IndexError) as exc:
            raise serializers.ValidationError("Invalid route geometry.") from exc
        return value


class HeatmapRequestSerializer(TripTimeSerializer):
    routes = RouteGeometrySerializer(many=True, allow_empty=False, max_length=3)
