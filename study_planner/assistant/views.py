from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from subjects.models import Subject
# Create your views here.
@login_required
def chat_view(request, chat_id=None):
    # Fetch all subjects to allow "Subject-Specific" AI chats
    subjects = Subject.objects.filter(user=request.user)
    
    # If a specific chat is selected
    active_chat = None
    messages = []
    if chat_id:
        # Logic to fetch messages for this specific conversation
        pass

    return render(request, "assistant/chat.html", {
        "subjects": subjects,
        "active_chat": active_chat,
    })