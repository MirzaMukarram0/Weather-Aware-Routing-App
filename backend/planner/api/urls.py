from django.urls import path

from planner.api import views

urlpatterns = [
    path("health", views.health),
    path("locations", views.locations),
    path("plan", views.plan),
    path("heatmap", views.heatmap),
]
