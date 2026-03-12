from django.contrib.auth.decorators import login_required
from .models import Exam,ExamAttempt
from django.shortcuts import render, redirect,get_object_or_404,reverse
from subjects.question_generator import generate_questions_from_pdf
import json
from django.http import JsonResponse
import time
from subjects.models import Chapter, Question,Subject
from django.contrib import messages

@login_required
def start_exam_view(request, subject_id):
    subject = get_object_or_404(
        Subject,
        id=subject_id,
        user=request.user
    )

    questions = Question.objects.filter(
        chapter__subject=subject
    )

    if not questions.exists():
        messages.error(request, "Generate exam questions first.")
        return redirect("subjects:subject_detail", subject_id=subject.id)

    return render(request, "exams/exam_mode.html", {
        "subject": subject,
        "questions": questions,
        "submit_url": reverse('exams:submit_exam', args=[subject.id]),
        "exam_type": "Final Subject Exam"
    })


def chapter_quiz_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    questions = Question.objects.filter(chapter=chapter)
    
    return render(request, "exams/exam_mode.html", {
        "subject": chapter.subject, 
        "questions": questions,
        "submit_url": reverse('exams:submit_chapter_quiz', args=[chapter.id]),
        "exam_type": f"Chapter {chapter.chapter_number} Quiz"
    })
@login_required
def submit_exam_view(request, subject_id):
    if request.method == "POST":
        subject = get_object_or_404(Subject, id=subject_id, user=request.user)
        # Gets all questions across all chapters for this subject
        questions = Question.objects.filter(chapter__subject=subject)
        
        score = 0
        total = questions.count()
        results_data = []

        for q in questions:
            # 1. Get the exact text the user submitted
            user_ans = request.POST.get(f'question_{q.id}', '').strip()
            is_correct = False
            
            # 2. Turn the saved options into a clean Python list
            options_list = [opt.strip() for opt in q.options_text.splitlines() if opt.strip()]
            
            user_letter = None
            letters = ['A', 'B', 'C', 'D']
            
            # 3. Figure out if the user picked the 1st(A), 2nd(B), 3rd(C), or 4th(D) option
            if user_ans in options_list:
                ans_index = options_list.index(user_ans)
                if ans_index < len(letters):
                    user_letter = letters[ans_index]
            
            # 4. Compare the user's mapped letter to the database correct letter
            correct_letter = q.correct_answer.strip().upper()
            
            if user_letter == correct_letter:
                is_correct = True
                score += 1
                
            # 5. Find the full text of the correct answer to show on the results page
            correct_text = "Unknown"
            if correct_letter in letters:
                c_index = letters.index(correct_letter)
                if c_index < len(options_list):
                    correct_text = options_list[c_index]
            
            results_data.append({
                'text': q.text,
                'user_ans': user_ans if user_ans else 'No Answer',
                'correct': f"{correct_letter}) {correct_text}",
                'is_correct': is_correct
            })

        # Save the attempt to the database
        ExamAttempt.objects.create(
            user=request.user,
            subject=subject,
            score=score,
            total_possible=total
        )

        return render(request, "exams/quiz_result.html", {
            "subject": subject,
            "score": score,
            "total": total,
            "results": results_data,
            "percentage": int((score / total) * 100) if total > 0 else 0,
            "exam_type": "Final Subject Exam"
        })

    return redirect("subjects:subject_list")
@login_required
def submit_chapter_quiz(request, chapter_id):
    if request.method == "POST":
        chapter = get_object_or_404(Chapter, id=chapter_id)
        questions = Question.objects.filter(chapter=chapter)
        
        score = 0
        results_data = []

        for q in questions:
            # 1. Get the exact text the user submitted
            user_ans = request.POST.get(f'question_{q.id}', '').strip()
            is_correct = False
            
            # 2. Turn the saved options into a clean Python list
            options_list = [opt.strip() for opt in q.options_text.splitlines() if opt.strip()]
            
            user_letter = None
            letters = ['A', 'B', 'C', 'D']
            
            # 3. Figure out if the user picked the 1st(A), 2nd(B), 3rd(C), or 4th(D) option
            if user_ans in options_list:
                ans_index = options_list.index(user_ans)
                if ans_index < len(letters):
                    user_letter = letters[ans_index]
            
            # 4. Compare the user's mapped letter to the database correct letter
            correct_letter = q.correct_answer.strip().upper()
            
            if user_letter == correct_letter:
                is_correct = True
                score += 1
                
            # 5. Find the full text of the correct answer to show on the results page
            correct_text = "Unknown"
            if correct_letter in letters:
                c_index = letters.index(correct_letter)
                if c_index < len(options_list):
                    correct_text = options_list[c_index]
            
            results_data.append({
                'text': q.text,
                'user_ans': user_ans if user_ans else 'No Answer',
                'correct': f"{correct_letter}) {correct_text}", # Now shows "D) Its drawback"
                'is_correct': is_correct
            })

        from .models import ChapterProgress 
        progress, _ = ChapterProgress.objects.get_or_create(user=request.user, chapter=chapter)
        progress.quiz_completed = True
        if score == questions.count() and questions.count() > 0:
            progress.is_mastered = True
        progress.save()

        return render(request, "exams/quiz_result.html", {
            "chapter": chapter,
            "score": score,
            "total": questions.count(),
            "results": results_data,
            "percentage": int((score / questions.count()) * 100) if questions.count() > 0 else 0
        })


@login_required
def practice_exam_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    questions = chapter.questions.all()
    return render(request, 'exams/exam_practice.html', {
        'chapter': chapter,
        'questions': questions
    })


@login_required
def exam_results_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    attempt = ExamAttempt.objects.filter(
        user=request.user, 
        chapter=chapter
    ).order_by('-completed_at').first()

    return render(request, 'exams/exam_results.html', {
        'attempt': attempt,
        'chapter': chapter  
    })

    
@login_required
def save_score_view(request, chapter_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        ExamAttempt.objects.create(
            user=request.user,
            chapter_id=chapter_id,
            score=data.get('score', 0)
        )
        return JsonResponse({'status': 'ok'})