from django.db import models
from django.conf import settings
from subjects.models import Subject, Chapter


DAYS = [
    ("MON", "Monday"),
    ("TUE", "Tuesday"),
    ("WED", "Wednesday"),
    ("THU", "Thursday"),
    ("FRI", "Friday"),
    ("SAT", "Saturday"),
    ("SUN", "Sunday"),
]

class TimetableEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=DAYS)

    subject = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()

    is_break = models.BooleanField(default=False)  

    class Meta:
        ordering = ["day", "start_time"]
        unique_together = ("user", "day", "start_time")

    def __str__(self):
        return f"{self.user} {self.day} {self.subject}"




class StudySchedule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    task_type = models.CharField(
        max_length=20,
        choices=[
            ("study", "Study"),
            ("revision", "Revision"),
            ("practice", "Practice"),
            ("exam", "Exam Prep"),
        ]
    )

    priority = models.IntegerField(default=1)  # 1 = low, 5 = high
    generated_by_ai = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    is_completed = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.date} {self.subject.name} ({self.task_type})"

class StudyLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.ForeignKey("subjects.Subject", on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.IntegerField() 

    def __str__(self):
        return f"{self.user} - {self.subject.name} - {self.duration_minutes} mins"