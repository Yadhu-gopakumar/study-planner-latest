from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None  # ❌ completely removed

    email = models.EmailField(unique=True)

    objects = UserManager()  # ✅ REQUIRED

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # no username

    def __str__(self):
        # What admin & UI will show
        if self.first_name:
            return f"{self.first_name} ({self.email})"
        return self.email

class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
   
    learning_pace = models.CharField(
        max_length=20,
        choices=[
            ('slow', 'Slow'),
            ('medium', 'Medium'),
            ('fast', 'Fast'),
        ],
        default='medium'
    )

    def __str__(self):
        return f"{self.user.email} Profile"
