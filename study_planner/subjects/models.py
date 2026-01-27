from django.db import models
from django.conf import settings
import os
from django.db.models import Max

class Subject(models.Model):
    DIFFICULTY_CHOICES = [
        (1, 'Easy'),
        (2, 'Medium'),
        (3, 'Hard'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_chapters(self):
        return self.chapters.count()

    # def get_user_progress(self, user):
    #     from exams.models import ChapterProgress

    #     total = self.total_chapters
    #     completed = ChapterProgress.objects.filter(
    #         user=user,
    #         chapter__subject=self,
    #         is_mastered=True
    #     ).count()

    #     percent = (completed / total * 100) if total > 0 else 0
    #     return {
    #         "total": total,
    #         "completed": completed,
    #         "percent": percent
    #     }
    def get_user_progress(self, user):
        from exams.models import ChapterProgress

        chapters = self.chapters.all()
        total_chapters = chapters.count()
        if total_chapters == 0:
            return {
                "total": 0,
                "completed": 0,
                "percent": 0
            }

        progresses = ChapterProgress.objects.filter(
            user=user,
            chapter__in=chapters
        )

        # Sum per-chapter progress
        total_progress = 0
        mastered = 0

        for cp in progresses:
            total_progress += cp.progress_percentage
            if cp.is_mastered:
                mastered += 1

        percent = total_progress / total_chapters

        return {
            "total": total_chapters,
            "completed": mastered,      # fully mastered chapters
            "percent": int(percent)     # overall subject progress %
        }

    def __str__(self):
        return self.name

# class Subject(models.Model):
#     DIFFICULTY_CHOICES = [
#         (1, 'Easy'),
#         (2, 'Medium'),
#         (3, 'Hard'),
#     ]

#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE
#     )
#     name = models.CharField(max_length=200)
#     code = models.CharField(max_length=20)
#     difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES)
#     total_chapters = models.IntegerField(default=0)
#     completed_chapters = models.IntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)


#     def get_user_progress(self, user):
#         from exams.models import ChapterProgress

#         total = self.chapter_set.count()
#         completed = ChapterProgress.objects.filter(
#             user=user, 
#             chapter__subject=self, 
#             is_mastered=True
#         ).count()
        
#         percent = (completed / total * 100) if total > 0 else 0
#         return {
#             'total': total,
#             'completed': completed,
#             'percent': percent
#         }

#     def __str__(self):
#         return self.name


class Chapter(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')
    chapter_number = models.PositiveIntegerField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True)
    note_file = models.FileField(upload_to='chapters/notes/', null=True, blank=True)
    summary = models.TextField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    is_not_pdf=models.BooleanField(default=False)
    def is_pdf(self):
        return self.note_file and self.note_file.name.lower().endswith(".pdf")
    def save(self, *args, **kwargs):
        # 🔑 Auto-increment chapter number PER SUBJECT
        if not self.chapter_number:
            last_number = (
                Chapter.objects
                .filter(subject=self.subject)
                .aggregate(max_num=Max("chapter_number"))
                .get("max_num")
            )
            self.chapter_number = (last_number or 0) + 1

        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('subject', 'chapter_number') # Prevents duplicate chapter numbers
        ordering = ["chapter_number"]

class Question(models.Model):
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    text = models.TextField()

    options_text = models.TextField()
    correct_answer = models.CharField(max_length=1)  # A / B / C / D

    def __str__(self):
        return self.text
