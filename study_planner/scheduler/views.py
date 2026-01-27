from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from django.utils import timezone
from subjects.models import Subject
from exams.models import Exam
from .models import StudySchedule


# views.py
from django.shortcuts import render
from .models import Subject

def dashboard_view(request):
   
    context = {
        'today_schedule': [], # Your schedule logic here
    }
    return render(request, 'dashboard.html', context)

@login_required
def schedule_view(request):
    schedules = StudySchedule.objects.filter(
        user=request.user,
        date__gte=timezone.now().date()
    ).order_by("date", "priority")

    return render(
        request,
        "scheduler/schedule.html",
        {"schedules": schedules}
    )


@login_required
def generate_schedule_view(request):
    today = timezone.now().date()

    # If already generated, don’t duplicate
    if StudySchedule.objects.filter(user=request.user, date=today).exists():
        return redirect("dashboard")

    subjects = Subject.objects.filter(user=request.user)

    priority = 1
    for subject in subjects:
        StudySchedule.objects.create(
            user=request.user,
            subject=subject,
            date=today,
            time_allocated=2,   # default 2 hours
            priority=priority
        )
        priority += 1

    return redirect("dashboard")



# # views.py
# from django.http import JsonResponse
# from .models import ScheduleItem # Adjust to your model name

# def get_schedule_events(request):
#     # Fetch schedule items for the logged-in user
#     events = ScheduleItem.objects.filter(user=request.user)
    
#     event_list = []
#     for event in events:
#         event_list.append({
#             'title': event.subject.name,
#             'start': event.date.isoformat(), # Format: YYYY-MM-DD
#             'color': '#6C5DD3',              # Match your theme
#             'allDay': True,
#         })
#     return JsonResponse(event_list, safe=False)