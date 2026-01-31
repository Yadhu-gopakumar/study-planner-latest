from django.contrib import admin
from .models import *


admin.site.register(Exam)
admin.site.register(ExamAttempt)
admin.site.register(ChapterProgress)



@admin.register(Exam_time_table)
class ExamTimeTableAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "exam_date",
    )
    list_filter = ("exam_date",)
    search_fields = ("subject__name",)
