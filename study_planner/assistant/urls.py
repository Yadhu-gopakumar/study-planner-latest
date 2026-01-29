from django.urls import path
from . import views

app_name='assistant'
urlpatterns = [
# Chat / AI Tutor Interface
    path('chat/', views.chat_view, name='chat'),
    # path('chat/<int:subject_id>/', views.chat_view, name='chat_subject'),
]
