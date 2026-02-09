# exam/urls.py
from django.urls import path
from .views import *

app_name = "exams"

urlpatterns = [
    path("start-exam/<int:subject_id>/", start_exam_view, name="start_exam"),
    path("chapter-quiz/<int:chapter_id>/", chapter_quiz_view, name="chapter_quiz"), # Add this
    path("submit-exam/<int:subject_id>/", submit_exam_view, name="submit_exam"),
    path("submit-quiz/<int:chapter_id>/", submit_chapter_quiz, name="submit_chapter_quiz"), # Add this
    path("results/<int:chapter_id>/", exam_results_view, name="exam_results"),
]