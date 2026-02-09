from django.contrib.auth.decorators import login_required
from .models import Subject,Chapter,Question
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from .question_generator import generate_questions_from_pdf, extract_text_from_pdf
import requests
from google import genai
import traceback
from django.http import JsonResponse
from .question_generator import generate_questions_from_text
from openai import OpenAI
import json, os
import re
import pdfplumber
from dotenv import load_dotenv




@login_required
def subjects_list_view(request):
    subjects = Subject.objects.filter(
        user=request.user
    ).order_by('-created_at')

    difficulty_filter = request.GET.get('difficulty')
    if difficulty_filter:
        subjects = subjects.filter(difficulty=difficulty_filter)

    search_query = request.GET.get('search')
    if search_query:
        subjects = subjects.filter(name__icontains=search_query)

    for subject in subjects:
        stats = subject.get_user_progress(request.user)
        subject.progress_percent = stats["percent"]
        subject.completed = stats["completed"]
        subject.total = stats["total"]


    return render(
        request,
        'subjects/courses_page.html',
        {'subjects': subjects}
    )




@login_required
def add_subject_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        code = request.POST.get("code")
        difficulty = request.POST.get("difficulty")

        Subject.objects.create(
            user=request.user,
            name=name,
            code=code,
            difficulty=difficulty,
        )

        return redirect("subjects:subjects_list")

    return render(request, "subjects/add_subject_page.html")




@login_required
def edit_subject_view(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    
    if request.method == "POST":
        subject.name = request.POST.get("name")
        subject.code = request.POST.get("code")
        subject.difficulty = request.POST.get("difficulty")
        subject.total_chapters = request.POST.get("total_chapters")
        subject.save()
        messages.success(request, f"{subject.name} updated successfully!")
        return redirect("subjects:subjects_list")

    return render(request, "subjects/edit_subject.html", {"subject": subject})

@login_required
def delete_subject_view(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    
    if request.method == "POST":
        subject.delete()
        messages.success(request, "Subject deleted successfully.")
        return redirect("subjects:subjects_list")
        
    return render(request, "subjects/delete_confirm.html", {"subject": subject})



@login_required
def subject_detail_view(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    chapters = subject.chapters.all().order_by("chapter_number")
    chapter_map = {c.chapter_number: c for c in chapters}

    from exams.models import ChapterProgress
    mastered_ids = set(
        ChapterProgress.objects.filter(
            user=request.user,
            chapter__subject=subject,
            is_mastered=True
        ).values_list("chapter_id", flat=True)
    )

    chapter_slots = []
    total_slots = subject.total_chapters  

    for i in range(1, total_slots + 1):
        chapter = chapter_map.get(i)

        summary_preview = "No summary generated. Click below."
        if chapter and chapter.summary:
            try:
                data = json.loads(chapter.summary)
                summary_preview = data.get("summary_paragraph", summary_preview)
            except Exception:
                summary_preview = chapter.summary

        chapter_slots.append({
            "number": i,
            "data": chapter,
            "is_completed": chapter and chapter.id in mastered_ids,
            "summary_preview": (
                summary_preview[:120] + "..."
                if len(summary_preview) > 120
                else summary_preview
            )
        })

    progress = 0
    if total_slots > 0:
        progress = (len(mastered_ids) / total_slots) * 100

    context = {
        "subject": subject,
        "chapter_slots": chapter_slots,
        "progress": int(progress),
        "completed_chapters": len(mastered_ids),
        "total_chapters": total_slots,
    }

    return render(request, "subjects/detail.html", context)


@login_required
def add_chapter_view(request, subject_id):
    if request.method == "POST":
        subject = get_object_or_404(Subject, id=subject_id, user=request.user)
        title = request.POST.get("title")
        note_file = request.FILES.get("note_file")

        chapter = Chapter.objects.create(
            subject=subject,
            title=title,
            note_file=note_file
        )
        
     
        return redirect('subjects:subject_detail', subject_id=subject.id)


@login_required
def edit_chapter_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, subject__user=request.user)
    if request.method == "POST":
        chapter.title = request.POST.get("title")
        if request.FILES.get("note_file"):
            chapter.note_file = request.FILES.get("note_file")
            chapter.summary = ""
            chapter.questions.all().delete()
        chapter.save()
        return redirect('subjects:subject_detail', subject_id=chapter.subject.id)
    
    return render(request, 'subjects/edit_chapter.html', {'chapter': chapter})

@login_required
def delete_chapter_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, subject__user=request.user)
    subject_id = chapter.subject.id
    if request.method == "POST":
        chapter.delete()
    return redirect('subjects:subject_detail', subject_id=subject_id)



def extract_text_from_pdf(pdf_path):
    print("📄 Opening PDF:", pdf_path)
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        print("📑 Total pages:", len(pdf.pages))
        for idx, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                print(f"  ✅ Page {idx}: extracted {len(page_text)} chars")
                text += page_text + " "
            else:
                print(f"  ⚠️ Page {idx}: no text extracted")

    return text.strip()


# ---------------- TEXT CLEANING ----------------
def clean_text(text):
    print("🧹 Cleaning extracted text...")
    original_len = len(text)

    text = re.sub(r"[•●▪■►–—]", " ", text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    print(f"🧹 Text length before cleaning: {original_len}")
    print(f"🧹 Text length after cleaning:  {len(text)}")
    
    return text.strip()

def process_ai_view(request, chapter_id):
    print(f"\n[DEBUG] Starting AI summary for Chapter {chapter_id}", flush=True)

    chapter = get_object_or_404(
        Chapter, id=chapter_id, subject__user=request.user
    )

    if not chapter.note_file:
        messages.error(request, "No PDF file attached.")
        return redirect("subjects:subject_detail", subject_id=chapter.subject.id)

    # Avoid re-running AI
    if chapter.summary:
        print("[DEBUG] Summary already exists, skipping AI", flush=True)
        return redirect("subjects:chapter-summery", chapter_id=chapter.id)

    # Extract + clean PDF text
    print("[DEBUG] Extracting PDF text...", flush=True)
    raw_text = extract_text_from_pdf(chapter.note_file.path)
    pdf_text = clean_text(raw_text)

    if len(pdf_text) < 300:
        messages.warning(request, "Not enough readable content in PDF.")
        return redirect("subjects:subject_detail", subject_id=chapter.subject.id)

    # limit text for speed & quality
    pdf_text = pdf_text[:1200]

    try:
        print("[DEBUG] Calling DeepSeek API...", flush=True)

        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                  "role": "system",
                  "content": (
                      "You are an academic assistant for students.\n\n"

                      "TASK:\n"
                      "1. Write ONE SIMPLE paragraph summary using easy English.\n"
                      "   - Short sentences\n"
                      "   - One idea per sentence\n"
                      "   - Preserve equations, formulas, numbers, and symbols\n\n"

                      "2. Extract point-wise information ONLY IF it is explicitly mentioned in the text:\n"
                      "   - Applications\n"
                      "   - Advantages / Pros\n"
                      "   - Disadvantages / Demerits\n"
                      "   - Limitations / Challenges\n"
                      "   - Important key points\n\n"

                      "POINT RULES:\n"
                      "- Each point must be a short sentence\n"
                      "- Do NOT repeat the paragraph content verbatim\n\n"

                      "STRICT RULES:\n"
                      "- Do NOT invent information\n"
                      "- Do NOT add sections if they are not present in the text\n"
                      "- Use simple academic English only\n"
                      "- Do NOT use bullet symbols (*, -, •)\n\n"

                      "Return JSON ONLY in the following format:\n\n"
                      "{\n"
                      '  "summary_paragraph": "<paragraph>",\n'
                      '  "points": {\n'
                      '    "applications": [],\n'
                      '    "advantages": [],\n'
                      '    "disadvantages": [],\n'
                      '    "limitations": [],\n'
                      '    "key_points": []\n'
                      "  }\n"
                      "}"
                  )
                },
                {
                    "role": "user",
                    "content": pdf_text
                }
            ],
            response_format={ "type": "json_object" }
        )

        data = json.loads(response.choices[0].message.content)
        
        summary = data.get("summary_paragraph", "")
        points = data.get("points", {})
        
        final_data = {
            "summary_paragraph": summary,
            "points": points
        }
        
        chapter.summary = json.dumps(final_data, indent=2)
        chapter.save()
        from exams.models import ChapterProgress
        
        progress, created = ChapterProgress.objects.get_or_create(
            user=request.user,
            chapter=chapter
            )
        progress.summary_viewed = True
        progress.save()

        messages.success(request, "Summary generated successfully!")
        print("[DEBUG] Summary saved to Chapter model", flush=True)

    except Exception as e:
        print("[ERROR] DeepSeek failed:", e, flush=True)
        chapter.summary = "AI summary generation failed. Please try again later."
        chapter.save()
        messages.error(request, "AI service unavailable.")

    return redirect("subjects:chapter-summery", chapter_id=chapter.id)

import os
import json
import edge_tts
import asyncio
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404

def chapter_audio_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, subject__user=request.user)
    
    if not chapter.summary:
        return HttpResponse("No summary found", status=404)

    # 1. Define the file path
    audio_filename = f"chapter_audio_{chapter.id}.mp3"
    audio_dir = os.path.join(settings.MEDIA_ROOT, "audio_summaries")
    audio_path = os.path.join(audio_dir, audio_filename)

    # 2. Check if the file already exists
    if os.path.exists(audio_path):
        # If it exists, open and return the saved file
        return FileResponse(open(audio_path, 'rb'), content_type="audio/mpeg")

    # 3. If it doesn't exist, generate it
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir, exist_ok=True)

    data = json.loads(chapter.summary)
    full_text = f"Chapter Summary. {data.get('summary_paragraph', '')}. "
    points = data.get("points", {})
    for section_name, items in points.items():
        if items:
            full_text += f" {section_name.replace('_', ' ')}. " + " . ".join(items) + ". "

    async def save_audio():
        communicate = edge_tts.Communicate(full_text, "en-US-AriaNeural")
        # Save directly to the path
        await communicate.save(audio_path)

    try:
        asyncio.run(save_audio())
        # Return the newly created file
        return FileResponse(open(audio_path, 'rb'), content_type="audio/mpeg")
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)



def generate_exam_questions_view(request, chapter_id):
    chapter = get_object_or_404(
        Chapter, id=chapter_id, subject__user=request.user
    )

    if not chapter.summary:
        messages.error(request, "Generate summary first.")
        return redirect("subjects:view_ai_results", chapter_id=chapter.id)

    if chapter.questions.exists():
        return redirect("subjects:chapter-questions", chapter_id=chapter.id)

    try:
        summary_data = json.loads(chapter.summary)
        clean_text = summary_data.get("summary_paragraph", "")
        for pts in summary_data.get("points", {}).values():
            clean_text += " " + " ".join(pts)
    except Exception:
        clean_text = chapter.summary

    # Generate base question ideas (SEEDS)
    base_questions = generate_questions_from_text(clean_text, limit=10)

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )

    TARGET = 5
    MAX_ATTEMPTS = 10

    saved = 0
    attempts = 0

    base_questions = generate_questions_from_text(clean_text, limit=5)

    if not base_questions:
        messages.error(
            request,
            "Not enough content to generate exam questions."
        )
        return redirect("subjects:chapter-summery", chapter_id=chapter.id)

    while saved < TARGET and attempts < MAX_ATTEMPTS:
        attempts += 1

        q_text = base_questions[(attempts - 1) % len(base_questions)]

        prompt = f"""
You are an academic exam question setter.

Generate ONE high-quality MCQ.

RULES:
- Meaningful academic question
- No symbols like ", {{ }}, [ ]
- Exactly 4 options (A–D)
- One correct answer

Return JSON ONLY:

{{
  "question": "...",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct_answer": "A) ..."
}}

CONTENT:
{q_text}
"""

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=250,
            )

            data = json.loads(response.choices[0].message.content)

            question = data.get("question")
            options = data.get("options", [])
            correct = data.get("correct_answer")

            if (
                question
                and len(options) == 4
                and correct in options
                and not Question.objects.filter(
                    chapter=chapter, text=question
                ).exists()
            ):
                Question.objects.create(
                    chapter=chapter,
                    text=question,
                    options_text="\n".join(options),
                    correct_answer=correct
                )
                saved += 1

        except Exception as e:
            print("DeepSeek error:", e)
            
    from exams.models import ChapterProgress
    
    progress, created = ChapterProgress.objects.get_or_create(
        user=request.user,
        chapter=chapter
    )
    
    progress.questions_generated = True
    progress.save()
    
    messages.success(
        request,
        f"{saved} exam questions generated successfully!"
    )
    return redirect("subjects:chapter-questions", chapter_id=chapter.id)



@login_required
def view_ai_summary(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)

    summary_data = None
    formatted_points = []

    if chapter.summary:
        try:
            data = json.loads(chapter.summary)

            for key, items in data.get("points", {}).items():
                formatted_points.append({
                    "title": key.replace("_", " ").title(),
                    "items": items
                })

            summary_data = {
                "summary_paragraph": data.get("summary_paragraph", ""),
                "points": formatted_points
            }

        except json.JSONDecodeError:
            summary_data = None

    return render(request, "subjects/view_ai_results.html", {
        "chapter": chapter,
        "summary_data": summary_data,
    })


from django.shortcuts import get_object_or_404, render
from .models import Chapter

def view_ai_questions(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)

    questions = chapter.questions.all()  

    return render(
        request,
        "subjects/view_questions_from_chapter.html",
        {
            "chapter": chapter,
            "questions": questions,
        }
    )
