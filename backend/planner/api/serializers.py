from rest_framework import serializers


class LocationQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=200, allow_blank=False)


class PlanRequestSerializer(serializers.Serializer):
    origin_lat = serializers.FloatField()
    origin_lon = serializers.FloatField()
    origin_label = serializers.CharField(max_length=500, required=False, allow_blank=True)
    dest_lat = serializers.FloatField()
    dest_lon = serializers.FloatField()
    dest_label = serializers.CharField(max_length=500, required=False, allow_blank=True)
    departure = serializers.DateTimeField()
    timezone = serializers.CharField(max_length=64)
    load_lb = serializers.FloatField(min_value=1, max_value=80000)
    interval_mi = serializers.ChoiceField(choices=[10, 25, 50], default=25)


class HeatmapRequestSerializer(serializers.Serializer):
    departure = serializers.DateTimeField()
    timezone = serializers.CharField(max_length=64)
    load_lb = serializers.FloatField(min_value=1, max_value=80000)
    routes = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )
