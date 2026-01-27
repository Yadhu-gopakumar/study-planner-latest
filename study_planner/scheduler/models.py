from django.db import models
from django.conf import settings
from subjects.models import Subject

class Chapter(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=300)
    order = models.IntegerField()
    estimated_hours = models.FloatField(default=2.0)
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.subject.name} - {self.name}"


class StudySchedule(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    date = models.DateField()
    time_allocated = models.FloatField()  # hours
    priority = models.IntegerField(default=3)  # 1 = high
    is_completed = models.BooleanField(default=False)
    actual_time_spent = models.FloatField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user} - {self.subject} ({self.date})"
