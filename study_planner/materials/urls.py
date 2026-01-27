from django.urls import path
from .views import *

app_name="materials"
urlpatterns = [
    path("", materials_list_view, name="materials_list"),
    path('upload-handwritten/', upload_handwritten_view, name='upload_handwritten'),
    
    path('process-ai/<int:chapter_id>/', process_ai_view, name='process_ai_view'),
    path('chapter/<int:chapter_id>/delete/', delete_chapter_view, name='delete_chapter'),

]
