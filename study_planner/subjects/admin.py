from django.contrib import admin
from .models import Subject, Chapter, Question

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'user',
        'difficulty',
        'total_chapters',
        'created_at',
    )
    list_filter = (
        'difficulty',
        'created_at',
    )
    search_fields = (
        'name',
        'code',
    )
    readonly_fields = (
        'created_at',
    )

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = (
        'chapter_number',
        'title',
        'subject',
        'is_completed',
        'is_not_pdf',
    )
    list_filter = (
        'subject',
        'is_completed',
        'is_not_pdf',
    )
    search_fields = (
        'title',
    )
    ordering = (
        'subject',
        'chapter_number',
    )

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'text',
        'chapter',
        'correct_answer',
    )
    list_filter = (
        'chapter',
    )
    search_fields = (
        'text',
    )
