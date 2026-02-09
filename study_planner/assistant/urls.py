from django.urls import path
from . import views

app_name='assistant'
urlpatterns = [
    path('chat/', views.chat_view, name='chat'),
    path('chat/htmx/', views.chat_htmx, name='chat_htmx'),  
    path('chat/<int:subject_id>/', views.load_chat_history, name='load_history'),
    path('chat/delete/<int:subject_id>/', views.delete_chat, name='delete_chat'),
]
