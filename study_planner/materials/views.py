from django.contrib.auth.decorators import login_required
from django.shortcuts import render



import requests
import json
from django.shortcuts import get_object_or_404, redirect, render
from subjects.models import Chapter

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from subjects.models import Subject, Chapter,Question
from openai import OpenAI
import os

def call_deepseek_api(prompt: str) -> str:
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "You are an academic assistant. Clean OCR text and summarize clearly in simple English."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=600
    )

    return response.choices[0].message.content.strip()





@login_required
def materials_list_view(request):
  
    chapters_with_files = Chapter.objects.filter(
        subject__user=request.user, 
        note_file__isnull=False
    ).exclude(note_file='').select_related('subject')

    total_materials = chapters_with_files.count()
    pdf_count = total_materials 
    total_questions = Question.objects.filter(chapter__in=chapters_with_files).count()

    context = {
        'materials': chapters_with_files,
        'subjects': Subject.objects.filter(user=request.user),
        'total_materials': total_materials,
        'total_questions': total_questions,
        'pdf_count': pdf_count,
        'handwritten_count': 0, 
    }
    return render(request, 'materials/list.html', context)


@login_required
def upload_material_view(request):
    return render(request, "materials/upload.html")

def process_ai_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if not chapter.note_file:
        return redirect('subjects:subject_detail', subject_id=chapter.subject.id)

    try:
        print(chapter.note_file.path)
        # 1. OCR.space API Request
        with open(chapter.note_file.path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={chapter.note_file.path: f},
                data={
                    'apikey': 'K82275197288957', # Your key
                    'language': 'eng',
                    'isOverlayRequired': False,
                    'isTable': False,
                    'OCREngine': 2, 
                    'scale': True
                }
            )
        print(response)
        # Check if the HTTP request itself failed
        response.raise_for_status()
        result = response.json()
        
        if result.get('OCRExitCode') == 1:
            raw_text = ""
            # OCR.space returns a list of results (one per page)
            for res in result.get('ParsedResults'):
                raw_text += res.get('ParsedText') + "\n"
        else:
            # This catches specific API errors (like file too large or invalid key)
            error_message = result.get('ErrorMessage', ['Unknown OCR Error'])[0]
            raise Exception(f"OCR Error: {error_message}")

        summary_result = call_deepseek_api(f"The following is raw OCR text. Clean up typos and summarize clearly: {raw_text}")
        
        # 4. Save to Model
        chapter.summary = summary_result
        chapter.is_not_pdf=True
        chapter.save()
        
        return redirect('subjects:chapter-summary', chapter_id=chapter.id)

    except requests.exceptions.RequestException as e:
        return render(request, 'error.html', {'message': f'Network error: Could not connect to OCR service.'})
    except Exception as e:
        print(f"Error in OCR View: {e}")
        return render(request, 'error.html', {'message': str(e)})

@login_required
def upload_handwritten_view(request):
    if request.method == "POST":
        subject_id = request.POST.get('subject_id')
        title = request.POST.get('title')
        note_file = request.FILES.get('note_file')
        
        subject = get_object_or_404(Subject, id=subject_id, user=request.user)
        
        # Calculate next chapter number
        next_num = subject.chapters.count() + 1
        
        # Create the Chapter/Material
        new_chapter = Chapter.objects.create(
            subject=subject,
            chapter_number=next_num,
            title=title,
            note_file=note_file
        )

        return redirect('materials:process_ai_view', chapter_id=new_chapter.id)


@login_required
def delete_chapter_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, subject__user=request.user)
    if request.method == "POST":
        chapter.delete()
    return redirect('materials:materials_list',)
