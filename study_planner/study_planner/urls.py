from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # Admin (for testing & debugging)
    path("admin/", admin.site.urls),

    # Public homepage (landing page)
    # path("", include("core.urls")),

    # Authentication
    path("accounts/", include("accounts.urls")),

    # Main features
    path("subjects/", include("subjects.urls")),
    path("exams/", include("exams.urls")),
    path("materials/", include("materials.urls")),
    path("practice/", include("practice.urls")),

    # Dashboard & schedule (must NOT be empty path again)
    path("", include("scheduler.urls")),
]


# ✅ THIS IS REQUIRED
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )