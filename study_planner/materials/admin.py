from django.contrib import admin
from .models import StudyMaterial, ExtractedQuestion


@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'subject',
        'chapter',
        'material_type',
        'uploaded_at',
    )
    list_filter = (
        'material_type',
        'subject',
    )
    search_fields = (
        'title',
        'extracted_text',
    )
    readonly_fields = (
        'uploaded_at',
    )
    ordering = ('-uploaded_at',)


@admin.register(ExtractedQuestion)
class ExtractedQuestionAdmin(admin.ModelAdmin):
    list_display = (
        'question_text',
        'material',
        'difficulty',
        'times_practiced',
        'success_rate',
        'created_at',
    )
    list_filter = (
        'difficulty',
        'material',
    )
    search_fields = (
        'question_text',
    )
    readonly_fields = (
        'created_at',
    )
    ordering = ('-created_at',)
