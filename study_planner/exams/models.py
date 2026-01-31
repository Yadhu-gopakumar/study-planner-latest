from django.db import models
from django.conf import settings
from subjects.models import Chapter


class Exam_time_table(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True
    )

    subject = models.ForeignKey(
        "subjects.Subject",
        on_delete=models.CASCADE
    )

    exam_date = models.DateField()


    def __str__(self):
        return f"{self.subject.name} – {self.exam_date}"



class Exam(models.Model):
    subject = models.ForeignKey(
        "subjects.Subject",   
                on_delete=models.CASCADE
    )
    exam_name = models.CharField(max_length=200)
    exam_date = models.DateField()
    exam_time = models.TimeField()
    duration_minutes = models.IntegerField()
    total_marks = models.IntegerField(default=100)
    weightage = models.FloatField(default=1.0)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.exam_name} - {self.subject.name}"


class ExamAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.ForeignKey( "subjects.Subject", on_delete=models.CASCADE) 
    score = models.IntegerField(default=0)
    total_possible = models.IntegerField(default=0) 
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.subject.name} - {self.score}"



class ChapterProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chapter = models.ForeignKey( "subjects.Chapter", on_delete=models.CASCADE)
    
    # Progress Tracking Steps
    summary_viewed = models.BooleanField(default=False)
    questions_generated = models.BooleanField(default=False)
    quiz_completed = models.BooleanField(default=False)
    is_mastered = models.BooleanField(default=False) # Only True if they pass/get all correct
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'chapter') 

    def __str__(self):
        return f"{self.user.username} - {self.chapter.title} Progress"

    @property
    def progress_percentage(self):
        # Calculate a % based on booleans
        steps = [self.summary_viewed, self.questions_generated, self.quiz_completed]
        completed_steps = sum(1 for step in steps if step)
        return int((completed_steps / len(steps)) * 100)