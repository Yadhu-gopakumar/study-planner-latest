from django.db import models
from subjects.models import Subject


class StudyMaterial(models.Model):
    MATERIAL_TYPES = [
        ('pdf', 'PDF Notes'),
        ('handwritten', 'Handwritten Notes'),
        ('video', 'Video Link'),
        ('other', 'Other'),
    ]

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    from subjects.models import Chapter

    chapter = models.ForeignKey(
    Chapter,  
    on_delete=models.SET_NULL,
    null=True,
    blank=True
    )

    title = models.CharField(max_length=300)
    material_type = models.CharField(
        max_length=20,
        choices=MATERIAL_TYPES
    )
    file = models.FileField(
        upload_to='materials/',
        null=True,
        blank=True
    )
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ExtractedQuestion(models.Model):
    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE
    )
    question_text = models.TextField()
    difficulty = models.IntegerField(default=2)
    times_practiced = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text[:50]
