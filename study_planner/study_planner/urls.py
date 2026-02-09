from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    #login
    path("accounts/", include("accounts.urls")),

    # Main features
    path("subjects/", include("subjects.urls")),
    path("exams/", include("exams.urls")),
    path("materials/", include("materials.urls")),
    path("assistant/", include("assistant.urls")),


    # Dashboard & schedule
    path("", include("scheduler.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )