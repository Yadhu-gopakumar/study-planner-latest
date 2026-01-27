from django.urls import path
from .views import practice_home_view, start_practice_view

urlpatterns = [
    path("", practice_home_view, name="practice_home"),
    path("start/", start_practice_view, name="start_practice"),
]
