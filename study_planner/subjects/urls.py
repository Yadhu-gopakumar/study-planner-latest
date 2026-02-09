from django.urls import path
from .views import *

app_name='subjects'
urlpatterns = [
    path('', subjects_list_view, name='subjects_list'),
    path("add/", add_subject_view, name="add_subject"),
    path("add_chapter/<int:subject_id>/", add_chapter_view, name="add_chapter"),
    path('<int:subject_id>/', subject_detail_view, name='subject_detail'),
    path('<int:subject_id>/edit/', edit_subject_view, name='edit_subject'),
    path('<int:subject_id>/delete/', delete_subject_view, name='delete_subject'),
   
    # AI Processing and Results
    path('chapter/<int:chapter_id>/process/', process_ai_view, name='process_ai_view'),
    path('chapter/<int:chapter_id>/results/summery', view_ai_summary, name='chapter-summery'),
    path('chapter/<int:chapter_id>/results/questions', view_ai_questions, name='chapter-questions'),

    
    # Chapter Management (Edit/Delete)
    path('chapter/<int:chapter_id>/edit/', edit_chapter_view, name='edit_chapter'),
    path('chapter/<int:chapter_id>/delete/', delete_chapter_view, name='delete_chapter'),
    path("chapter/<int:chapter_id>/generate-exam/",generate_exam_questions_view,name="generate_exam_questions"),
    path('chapter/<int:chapter_id>/audio/', chapter_audio_view, name='chapter-audio'),
    ]
