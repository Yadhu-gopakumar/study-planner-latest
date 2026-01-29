from django.contrib import admin
from .models import TimetableEntry, StudySchedule


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "day",
        "start_time",
        "end_time",
        "subject",
        "is_break",
    )

    list_filter = (
        "day",
        "is_break",
    )

    search_fields = (
        "subject",
        "user__username",
    )

    ordering = (
        "day",
        "start_time",
    )

@admin.register(StudySchedule)
class StudyScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "date",
        "start_time",
        "end_time",
        "subject",
        "task_type",
        "priority",
        "generated_by_ai",
    )

    list_filter = (
        "task_type",
        "generated_by_ai",
        "date",
    )

    search_fields = (
        "subject__name",
        "user__username",
    )

    ordering = (
        "date",
        "start_time",
    )
