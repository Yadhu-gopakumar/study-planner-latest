from django.db import models
from django.conf import settings
from subjects.models import Subject
from materials.models import ExtractedQuestion

class MockTest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    title = models.CharField(
        max_length=200,
        default='Practice Test'
    )
    total_questions = models.IntegerField()
    duration_minutes = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class TestQuestion(models.Model):
    mock_test = models.ForeignKey(
        MockTest,
        on_delete=models.CASCADE
    )
    question = models.ForeignKey(
        ExtractedQuestion,
        on_delete=models.CASCADE
    )
    order = models.IntegerField()

    def __str__(self):
        return f"{self.mock_test} - Q{self.order}"
