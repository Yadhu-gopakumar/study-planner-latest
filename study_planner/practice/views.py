from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import MockTest, TestQuestion
from materials.models import ExtractedQuestion


@login_required
def practice_home_view(request):
    return render(request, "practice/home.html")


@login_required
def start_practice_view(request):
    if request.method == "POST":
        subject_id = request.POST.get("subject_id")

        questions = ExtractedQuestion.objects.filter(
            material__subject_id=subject_id
        )[:10]

        test = MockTest.objects.create(
            user=request.user,
            subject_id=subject_id,
            total_questions=len(questions)
        )

        for i, q in enumerate(questions, start=1):
            TestQuestion.objects.create(
                mock_test=test,
                question=q,
                order=i
            )

        return redirect("dashboard")

    return redirect("practice_home")
