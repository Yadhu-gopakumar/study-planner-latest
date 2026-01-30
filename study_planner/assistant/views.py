import json
from django.shortcuts import render,HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import os
from subjects.models import Subject
from subjects.models import Chapter
from openai import OpenAI
from .models import ChatSession,ChatMessage

client = OpenAI(
    # api_key=settings.DEEPSEEK_API_KEY,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

MAX_CHARS = 12000  # safe for DeepSeek

def get_subject_context(subject):
    chapters = subject.chapters.all().order_by("chapter_number")
    context = ""

    for ch in chapters:
        if ch.summary:
            block = f"\nChapter {ch.chapter_number}: {ch.title}\n{ch.summary}\n"
            if len(context) + len(block) > MAX_CHARS:
                break
            context += block

    return context



def deepseek_chat(question, subject_context):
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI tutor for a student. "
                f"Here are the syllabus notes: {subject_context} "  # <-- Added context here
                "Answer strictly using the provided syllabus notes above. "
                "Do not use outside knowledge. "
                "If the answer is not found in the notes, reply exactly: "
                "'This topic is not covered in your syllabus.'"
            )
        },
        {
            "role": "user",
            "content": question
        }
    ]

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.3
    )

    return response.choices[0].message.content


@login_required
def chat_view(request):
    subjects = Subject.objects.filter(user=request.user)
    # This example loads the most recent session's messages
    # You could also pass a session_id in the URL to load specific ones
    last_session = ChatSession.objects.filter(user=request.user).last()
    history = []
    if last_session:
        history = last_session.messages.all().order_by('created_at')

    return render(request, "assistant/chat.html", {
        "subjects": subjects,
        "history": history,
    })

@login_required
def chat_htmx(request):
    question = request.POST.get("question")
    subject_id = request.POST.get("subject_id")

    if not subject_id:
        # Return a small snippet if no subject selected
        return HttpResponse("<div class='text-red-500 p-2'>Please select a subject first.</div>")

    try:
        subject = Subject.objects.get(id=subject_id, user=request.user)
        
        # 1. Get or Create a Session for this user and subject
        session, created = ChatSession.objects.get_or_create(
            user=request.user, 
            subject=subject
        )

        # 2. Get the context from chapters
        context = get_subject_context(subject)

        # 3. Get AI Response
        reply = deepseek_chat(question, context)

        # 4. Save User Message
        ChatMessage.objects.create(
            session=session,
            role="user",
            content=question
        )

        # 5. Save AI Message
        ChatMessage.objects.create(
            session=session,
            role="ai",
            content=reply
        )

        return render(request, "assistant/partials/ai_message.html", {
            "reply": reply,
            "question": question
        })
        
    except Subject.DoesNotExist:
        return HttpResponse("Subject not found.", status=404)

from django.shortcuts import get_object_or_404

@login_required
def load_chat_history(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    
    # Get or create the session
    session, created = ChatSession.objects.get_or_create(user=request.user, subject=subject)
    
    # Get all messages for this session
    messages = session.messages.all().order_by('created_at')
    
    return render(request, "assistant/partials/chat_history.html", {
        "subject": subject,
        "messages": messages,
    })


from django.http import HttpResponse

@login_required
def delete_chat(request, subject_id):
    # Find and delete the session and its messages
    ChatSession.objects.filter(user=request.user, subject_id=subject_id).delete()
    
    # Return the "Initial State" HTML fragment to clear the UI
    initial_html = """
        <div id="initial-state" class="h-full flex flex-col items-center justify-center text-center space-y-4">
            <div class="text-6xl">📥</div>
            <h3 class="text-xl font-bold text-indigo-900">Conversation Cleared</h3>
            <p class="text-gray-500 max-w-xs">Your history for this subject has been deleted. Start a new chat below.</p>
        </div>
        <div id="new-messages-target"></div>
    """
    return HttpResponse(initial_html)