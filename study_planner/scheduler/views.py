from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect,get_object_or_404
from exams.models import Exam,Exam_time_table,ExamAttempt,ChapterProgress
from django.db.models import Max,Min
from .forms import TimetableEntryForm
from .models import StudySchedule, TimetableEntry,StudyLog
import os
from django.conf import settings
import joblib
from django.db.models import Sum, Avg, Count, F,Q
from subjects.models import Subject, Chapter
from django.http import JsonResponse
import json
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta, time,date
from django.http import HttpResponse

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
    user = request.user
    now_ist = timezone.localtime()
    today = now_ist.date()
    today_weekday = today.strftime("%a").upper()[:3]

    # 1. TIMETABLE & DAILY SESSIONS
    timetable_entries = TimetableEntry.objects.filter(user=user, day=today_weekday).order_by("start_time")
    study_sessions = StudySchedule.objects.filter(user=user, date=today).select_related("subject").order_by("start_time")

    # 2. DAILY PROGRESS
    total_tasks = study_sessions.count()
    completed_tasks = study_sessions.filter(is_completed=True).count()
    progress_percent = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

    # 3. GLOBAL STATS
    total_mins = StudyLog.objects.filter(user=user).aggregate(total=Sum('duration_minutes'))['total'] or 0
    study_hours = round(total_mins / 60, 1)

    avg_score_data = ExamAttempt.objects.filter(user=user).aggregate(
        avg_perc=Avg(F('score') * 100.0 / F('total_possible'))
    )
    overall_avg = round(avg_score_data['avg_perc'], 1) if avg_score_data['avg_perc'] else 0
    
    # Global Mastery Count (Total for all subjects)
    global_mastered_count = ChapterProgress.objects.filter(user=user, is_mastered=True).count()

    # 4. SUBJECT-SPECIFIC DATA (The loop only handles subject card info)
    subjects = Subject.objects.filter(user=user)
    # 2. ATTACH DATA (The "Magic" Step)
    for subject in subjects:
        # Calculate Time
        s_mins = StudyLog.objects.filter(user=user, subject=subject).aggregate(total=Sum('duration_minutes'))['total'] or 0
        subject.total_hours = round(s_mins / 60, 1)
        
        # Calculate Performance
        s_avg = ExamAttempt.objects.filter(user=user, subject=subject).aggregate(
            avg=Avg(F('score') * 100.0 / F('total_possible'))
        )['avg'] or 0
        subject.avg_performance = round(s_avg, 1)

        # Calculate Syllabus/Mastery
        total_ch = Chapter.objects.filter(subject=subject).count()
        mastered_ch = ChapterProgress.objects.filter(user=user, chapter__subject=subject, is_mastered=True).count()
        
        if total_ch > 0:
            subject.progress_percent = int((mastered_ch / total_ch) * 100)
        else:
            subject.progress_percent = 0
            

    # 3. GLOBAL STATS
    total_mins = StudyLog.objects.filter(user=user).aggregate(total=Sum('duration_minutes'))['total'] or 0
    study_hours = round(total_mins / 60, 1)
    
    avg_data = ExamAttempt.objects.filter(user=user).aggregate(avg=Avg(F('score') * 100.0 / F('total_possible')))
    overall_avg = round(avg_data['avg'], 1) if avg_data['avg'] else 0

    # 4. CHART DATA
    last_7_days, study_data, exam_data = [], [], []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        last_7_days.append(date.strftime("%b %d"))
        
        d_mins = StudyLog.objects.filter(user=user, start_time__date=date).aggregate(t=Sum('duration_minutes'))['t'] or 0
        study_data.append(round(d_mins / 60, 1))
        
        d_ex = ExamAttempt.objects.filter(user=user, completed_at__date=date).aggregate(a=Avg(F('score') * 100.0 / F('total_possible')))['a'] or 0
        exam_data.append(round(d_ex, 1))

    context = {
                "progress_percent": progress_percent,
                "overall_avg": overall_avg,
                "today": today,
                "timetable_entries": timetable_entries,
                "study_sessions": study_sessions,
                "subjects": subjects,
                "study_hours": study_hours,
                "overall_avg": overall_avg,
                "chart_labels": json.dumps(last_7_days),
                "chart_study_data": json.dumps(study_data),
                "chart_exam_data": json.dumps(exam_data),
                "mastered_count": ChapterProgress.objects.filter(user=user, is_mastered=True).count(),
        }

    return render(request, "dashboard.html", context)

@login_required
def schedule_view(request):
    try:
        week_offset = int(request.GET.get('week', 0))
    except (ValueError, TypeError):
        week_offset = 0

    today = timezone.localtime().date()   
    week_start = (today - timedelta(days=today.weekday())) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    # 1. FIND THE BOUNDARIES
    # Start: When you began your AI plan
    # End: The day BEFORE your very first exam starts
    active_range = StudySchedule.objects.filter(user=request.user).aggregate(
        plan_start=Min('date')
    )
    first_exam = Exam_time_table.objects.filter(user=request.user).aggregate(
        first_date=Min('exam_date')
    )

    plan_start = active_range['plan_start'] or today
    # The study period ends exactly one day before the first exam
    study_period_end = (first_exam['first_date'] - timedelta(days=1)) if first_exam['first_date'] else today

    # 2. Fetch data for this week
    ai_schedules = StudySchedule.objects.filter(
        user=request.user,
        date__range=(week_start, week_end)
    ).select_related("subject")

    routine_entries = TimetableEntry.objects.filter(user=request.user)
    
    # Get the exams happening this week to show them on the grid
    exams_this_week = Exam_time_table.objects.filter(
        user=request.user,
        exam_date__range=(week_start, week_end)
    )

    week_days = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        day_name = day_date.strftime("%a").upper()[:3]

        is_study_period = plan_start <= day_date <= study_period_end
        exam_on_this_day = exams_this_week.filter(exam_date=day_date).first()

        week_days.append({
            "name": day_date.strftime("%A"),
            "date": day_date,
            "is_today": day_date == today,
            "is_study_period": is_study_period,
            "exam": exam_on_this_day,
            "sessions": ai_schedules.filter(date=day_date).order_by("start_time"),
            "routine": routine_entries.filter(day=day_name) if is_study_period else []
        })
    # --- Calculate Weekly Progress ---
    subjects_progress = []
    # Get all unique subjects that have sessions scheduled for this specific week
    scheduled_subjects = Subject.objects.filter(
        studyschedule__user=request.user,
        studyschedule__date__range=(week_start, week_end)
    ).distinct()

    for subj in scheduled_subjects:
        # Get all sessions for this subject this week
        week_sessions = ai_schedules.filter(subject=subj)
        
        # Calculate total planned minutes
        planned_mins = 0
        completed_mins = 0
        
        for s in week_sessions:
            # Calculate duration of the session
            start_dt = datetime.combine(date.min, s.start_time)
            end_dt = datetime.combine(date.min, s.end_time)
            duration = (end_dt - start_dt).seconds / 60
            
            planned_mins += duration
            if s.is_completed:
                completed_mins += duration

        # Convert to hours for the UI
        planned_h = round(planned_mins / 60, 1)
        completed_h = round(completed_mins / 60, 1)
        
        # Calculate percent
        percent = int((completed_mins / planned_mins * 100)) if planned_mins > 0 else 0
        subjects_progress.append({
            "name": subj.name,
            "planned_hours": planned_h,
            "completed_hours": completed_h,
            "progress_percent": percent
        })

    return render(request, "scheduler/schedule.html", {
        "current_week_start": week_start,
        "current_week_end": week_end,
        "week_days": week_days,
        "week_offset": week_offset,
        "today_sessions": ai_schedules.filter(date=today).order_by("start_time"),
        "subjects_progress": subjects_progress,
    })


@login_required
def generate_schedule_form(request):
    subjects = Subject.objects.filter(user=request.user)

    if request.method == "POST":
        return redirect("scheduler:generate_schedule_create")

    return render(
        request,
        "scheduler/generate_schedule_form.html",
        {"subjects": subjects}
    )


def normalize_time(plans, daily_hours, user, break_minutes=15):
    """
    Fits proportions into the daily window, adjusted for user learning pace.
    """
    total_minutes = daily_hours * 60
    num_breaks = max(0, len(plans) - 1)
    breaks = num_breaks * break_minutes
    available = total_minutes - breaks

    # 1. Determine Learning Pace Multiplier
    # Default to medium (1.0) if profile doesn't exist
    pace_multiplier = 1.0
    try:
        pace = user.profile.learning_pace
        if pace == 'slow':
            pace_multiplier = 1.3  # Boost time needed
        elif pace == 'fast':
            pace_multiplier = 0.8  # Needs less time, more efficient
    except AttributeError:
        pass

    # 2. Calculate adjusted weights
    for p in plans:
        # Start with the base AI allocation
        weight = p["time_alloc"]
        
        # Apply Difficulty Boost (3 = Hard)
        if p["subject"].difficulty == 3:
            weight *= 1.5
            
        # Apply Personalized Learning Pace
        # multiply the weight by the pace_multiplier
        p["adjusted_weight"] = weight * pace_multiplier

    # 3. Sum up the new weights
    total_weight = sum(p["adjusted_weight"] for p in plans)
    
    if total_weight <= 0:
        for p in plans:
            p["minutes"] = available // len(plans) if plans else 0
        return plans

    # 4. Final Allocation
    for p in plans:
        calculated_minutes = int((p["adjusted_weight"] / total_weight) * available)
        
        # 30-minute floor to ensure meaningful study added by myself
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

    today = timezone.localtime().date()
    daily_hours = int(request.POST.get("hours_per_day", 4))
    start_h, start_m = map(int, request.POST.get("start_time", "18:00").split(":"))

    StudySchedule.objects.filter(user=request.user, date__gte=today).delete()
    TimetableEntry.objects.filter(user=request.user).delete()
    Exam_time_table.objects.filter(user=request.user).delete()

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
        plans = normalize_time(plans, daily_hours,request.user)

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
    
    now = timezone.localtime()
    today = now.date()


    schedules = StudySchedule.objects.filter(user=request.user, date=today)
    
    for s in schedules:
        start_dt = f"{s.date.isoformat()}T{s.start_time.strftime('%H:%M:%S')}"
        end_dt = f"{s.date.isoformat()}T{s.end_time.strftime('%H:%M:%S')}"
        
        events.append({
            "id": f"schedule-{s.id}",  # Unique ID for the JS Set
            "title": f"📘 {s.subject.name}",
            "start": start_dt,
            "end": end_dt,
            "backgroundColor": "#6366F1",
            "borderColor": "transparent",
            "is_completed": s.is_completed, 
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


@login_required
def toggle_study_completion(request, id):
    session = get_object_or_404(StudySchedule, id=id, user=request.user)
    session.is_completed = not session.is_completed
    session.save()

    # Calculate new progress
    today = session.date
    total = StudySchedule.objects.filter(user=request.user, date=today).count()
    completed = StudySchedule.objects.filter(user=request.user, date=today, is_completed=True).count()
    percent = int((completed / total) * 100) if total > 0 else 0

    return JsonResponse({
        "status": "success", 
        "is_completed": session.is_completed,
        "progress_percent": percent
    })



@login_required
def save_study_log(request):
    if request.method == "POST":
        data = json.loads(request.body)
        
        # 1. Create the Log
        StudyLog.objects.create(
            user=request.user,
            subject_id=data['subject_id'],
            start_time=data['start_time'],
            duration_minutes=data['duration']
        )

        # 2. Auto-complete today's schedule for this subject
        now = timezone.localtime()
        today = now.date()

        StudySchedule.objects.filter(
            user=request.user, 
            subject_id=data['subject_id'], 
            date=today
        ).update(is_completed=True)

        return JsonResponse({"status": "success"})




@login_required
def stop_schedule(request):
    # DELETE method to match hx-delete
    if request.method == "DELETE":
        today = timezone.localtime().date()
        StudySchedule.objects.filter(user=request.user, date=today).delete()
        
        # Return a success message or an empty div to clear the UI
        return HttpResponse("""
            <div class="p-6 text-center bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
                <p class="text-gray-500">Schedule cleared successfully.</p>
            </div>
        """)
    return HttpResponse("Method not allowed", status=405)