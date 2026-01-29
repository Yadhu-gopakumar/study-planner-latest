from django.urls import path
from .views import (
    dashboard_view,
    schedule_view,
    get_schedule_events,
    add_timetable_entry,
    timetable_list,
    generate_schedule_form,
    generate_schedule_create
)

app_name="scheduler"
urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("schedule/", schedule_view, name="schedule_view"),
    # path("generate/", generate_schedule_view, name="generate_schedule"),
    # scheduler/urls.py
    path("api/get-schedule-events/", get_schedule_events, name="get_schedule_events"),

    path(
        "schedule/generate/",
        generate_schedule_form,
        name="generate_schedule_form"
    ),
    path(
        "schedule/generate/create/",
        generate_schedule_create,
        name="generate_schedule_create"
    ),
    path("timetable/add/", add_timetable_entry, name="add_timetable"),
    path("timetable/", timetable_list, name="timetable_list"),
]

