from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from django.utils import timezone
from subjects.models import Subject
from exams.models import Exam,Exam_time_table
from django.http import JsonResponse
from django.db.models import Max
from datetime import time, timedelta,datetime
from .forms import TimetableEntryForm
from .models import StudySchedule, TimetableEntry
import os
from django.conf import settings
import joblib

MODEL_PATH = os.path.join(
    settings.BASE_DIR,
    "scheduler",
    "ml_models",
    "study_planner.pkl"
)
_study_model = None


def get_study_model():
    global _study_model
    if _study_model is None:
        _study_model = joblib.load(MODEL_PATH)
    return _study_model


@login_required
def dashboard_view(request):
    today = timezone.now().date()
    today_weekday = today.strftime("%a").upper()[:3]  # MON, TUE, ...

    # Fixed timetable (classes / routine)
    timetable_entries = TimetableEntry.objects.filter(
        user=request.user,
        day=today_weekday
    ).order_by("start_time")

    # Generated study schedule
    study_sessions = StudySchedule.objects.filter(
        user=request.user,
        date=today
    ).select_related("subject").order_by("start_time")

    context = {
        "today": today,
        "timetable_entries": timetable_entries,
        "study_sessions": study_sessions,
    }

    return render(request, "dashboard.html", context)

@login_required
def schedule_view(request):
    today = timezone.now().date()

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    schedules = StudySchedule.objects.filter(
        user=request.user,
        date__range=(week_start, week_end)
    ).select_related("subject")

    today_sessions = schedules.filter(date=today).order_by("start_time")

    week_days = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week_days.append({
            "name": day_date.strftime("%A"),
            "date": day_date,
            "is_today": day_date == today,
            "sessions": schedules.filter(date=day_date).order_by("start_time")
        })

    return render(request, "scheduler/schedule.html", {
        "current_week_start": week_start,
        "current_week_end": week_end,
        "week_days": week_days,
        "today_sessions": today_sessions,   # 🔥 NEW
    })

@login_required
def generate_schedule_form(request):
    subjects = Subject.objects.filter(user=request.user)

    if request.method == "POST":
        # handle later in generate_schedule_create
        return redirect("scheduler:generate_schedule_create")

    return render(
        request,
        "scheduler/generate_schedule_form.html",
        {"subjects": subjects}
    )

from datetime import datetime,date
from django.shortcuts import redirect
from django.utils import timezone

from datetime import datetime, timedelta, time
from django.utils import timezone
from datetime import date


def normalize_time(plans, daily_hours, break_minutes=15):
    """
    Takes the ML-predicted time_alloc (proportions) and fits them 
    into the user's actual available daily window.
    """
    total_minutes = daily_hours * 60
    num_breaks = max(0, len(plans) - 1)
    breaks = num_breaks * break_minutes
    available = total_minutes - breaks

    # Sum up predicted hours to get the total proportional weight
    raw_sum = sum(p["time_alloc"] for p in plans)
    
    # Safeguard against zero predictions
    if raw_sum <= 0:
        for p in plans:
            p["minutes"] = available // len(plans) if plans else 0
        return plans

    for p in plans:
        if p["subject"].difficulty == 3:
            p["time_alloc"] *= 1.5  # boost for Hard subjects
        calculated_minutes = int((p["time_alloc"] / raw_sum) * available)
        
        # Ensure a minimum study block of 30 minutes 
        p["minutes"] = max(30, calculated_minutes)

    return plans

def round_time_to_5(dt):
    """Rounds a datetime object down to the nearest 5-minute mark."""
    minute = (dt.minute // 5) * 5
    return dt.replace(minute=minute, second=0, microsecond=0)
def ml_allocate_time(subjects, daily_hours):
    model = get_study_model()
    plans = []

    for item in subjects:
        days_left = item.get("days_left", 1)
        X = [[
            int(item["subject"].difficulty),
            float(daily_hours),
            int(days_left),
            float(item.get("previous_score", 60))
        ]]

        # The model prediction
        prediction = model.predict(X)[0]
        time_alloc, predicted_priority, revision = prediction

        plans.append({
            "subject": item["subject"],
            "time_alloc": float(time_alloc),
            "raw_priority": float(predicted_priority), 
            "revision": max(1, int(revision)),
        })

    # --- COMPARATIVE RANKING ---
    # Sort subjects by the raw priority score (lower is higher priority)
    plans.sort(key=lambda x: x["raw_priority"])

    for index, p in enumerate(plans):
        # Assign unique priorities (1, 2, 3...) based on rank
        p["priority"] = index + 1 

    return plans
    



@login_required
def generate_schedule_create(request):
    if request.method != "POST":
        return redirect("scheduler:schedule_view")

    today = timezone.now().date()
    daily_hours = int(request.POST.get("hours_per_day", 4))
    start_h, start_m = map(int, request.POST.get("start_time", "18:00").split(":"))

    # 1. Clear future data only
    StudySchedule.objects.filter(user=request.user, date__gte=today).delete()
    TimetableEntry.objects.filter(user=request.user).delete()

    selected = []
    for key in request.POST:
        if key.startswith("subjects[") and key.endswith("][id]"):
            idx = key.split("[")[1].split("]")[0]
            sid = request.POST.get(f"subjects[{idx}][id]")
            ed = request.POST.get(f"subjects[{idx}][exam_date]")

            if not sid or not ed: continue

            subject = Subject.objects.get(id=sid, user=request.user)
            exam_date = date.fromisoformat(ed)

            # Fetch the maximum mark obtained for this subject from completed exams
            # looks for the highest 'total_marks' among exams marked as completed
            max_score_data = Exam.objects.filter(
                subject=subject, 
                is_completed=True
            ).aggregate(Max('total_marks'))
            
            # Use the max score if it exists, otherwise default to 60 as a baseline
            previous_score = max_score_data['total_marks__max'] if max_score_data['total_marks__max'] is not None else 60

            # Update or create the exam timetable entry
            Exam_time_table.objects.update_or_create(
                user=request.user, subject=subject,
                defaults={"exam_date": exam_date}
            )

            selected.append({
                "subject": subject,
                "difficulty": subject.difficulty,
                "available_hours": daily_hours,
                "days_left": max(1, (exam_date - today).days),
                "previous_score": previous_score, 
                "revision_freq": 1,
                "exam_date": exam_date
            })

    if not selected:
        return redirect("scheduler:schedule_view")

    # 2. Find the furthest exam date
    last_exam_date = max(s['exam_date'] for s in selected)
    
    loop_date = today
    while loop_date < last_exam_date:
        for s in selected:
            s["days_left"] = max(1, (s["exam_date"] - loop_date).days)

        plans = ml_allocate_time(selected, daily_hours)
        plans = normalize_time(plans, daily_hours)

        current_dt = datetime.combine(loop_date, time(start_h, start_m))

       
        # Create entries for the subjects allocated for this day
        for i, p in enumerate(plans):
            if p["minutes"] <= 0: continue

            # Calculate session start and end
            start = round_time_to_5(current_dt)
            end = round_time_to_5(start + timedelta(minutes=p["minutes"]))

            # 1. Create the Study session (Calendar View)
            StudySchedule.objects.create(
                user=request.user,
                subject=p["subject"],
                date=loop_date,
                start_time=start.time(),
                end_time=end.time(),
                task_type="study",
                priority=p["priority"],
                generated_by_ai=True
            )

            # Create the Study entry (Weekly Timetable View)
            if (loop_date - today).days < 7:
                TimetableEntry.objects.update_or_create(
                    user=request.user,
                    day=loop_date.strftime("%a").upper()[:3],
                    start_time=start.time(),
                    defaults={
                        'subject': p["subject"].name,
                        'end_time': end.time(),
                        'is_break': False
                    }
                )

            # Prepare for the next session or break
            current_dt = end

            # 3. Handle the Break between subjects
            if i < len(plans) - 1:
                break_start = current_dt
                break_end = break_start + timedelta(minutes=15)

                if (loop_date - today).days < 7:
                    TimetableEntry.objects.update_or_create(
                        user=request.user,
                        day=loop_date.strftime("%a").upper()[:3],
                        start_time=break_start.time(),
                        defaults={
                            'subject': "Break",
                            'end_time': break_end.time(),
                            'is_break': True
                        }
                    )
                current_dt = break_end
        loop_date += timedelta(days=1)

    return redirect("scheduler:schedule_view")

@login_required
def add_timetable_entry(request):
    if request.method == "POST":
        form = TimetableEntryForm(request.POST)
        if form.is_valid():
            timetable = form.save(commit=False)
            timetable.user = request.user
            timetable.save()
            return redirect("scheduler:timetable_list")
    else:
        form = TimetableEntryForm()

    return render(
        request,
        "scheduler/add_timetable.html",
        {"form": form}
    )

@login_required
def timetable_list(request):
    entries = TimetableEntry.objects.filter(
        user=request.user
    ).order_by("day", "start_time")

    return render(
        request,
        "scheduler/timetable_list.html",
        {"entries": entries}
    )


@login_required
def get_schedule_events(request):
    events = []
    
    # Get today's date based on server time
    today = timezone.now().date()

    schedules = StudySchedule.objects.filter(user=request.user, date=today)
    
    for s in schedules:
        start_dt = f"{s.date.isoformat()}T{s.start_time.strftime('%H:%M:%S')}"
        end_dt = f"{s.date.isoformat()}T{s.end_time.strftime('%H:%M:%S')}"
        
        events.append({
            "title": f"📘 {s.subject.name}",
            "start": start_dt,
            "end": end_dt,
            "backgroundColor": "#6366F1",
            "borderColor": "transparent",
            "extendedProps": {
                "description": f"Task {s.task_type}<br><b>Priority:</b> {s.priority}"
            }
        })

    # Exams 
    exams = Exam_time_table.objects.filter(user=request.user)
    for exam in exams:
        events.append({
            "title": f"📝 {exam.subject.name} - Exam",
            "start": exam.exam_date.isoformat(),
            "allDay": True,
            "backgroundColor": "#F87171",  
            "borderColor": "transparent",
            "extendedProps": {
                "description": f"{exam.subject.name}<br><b>Date:</b> {exam.exam_date}"
            }
        })

    return JsonResponse(events, safe=False)