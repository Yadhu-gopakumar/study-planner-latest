from django.urls import path
from .views import (
    dashboard_view,
    schedule_view,
    generate_schedule_view,
)

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("schedule/", schedule_view, name="schedule_view"),
    path("generate/", generate_schedule_view, name="generate_schedule"),
]
