from django.urls import path, include

urlpatterns = [
    path("", include("research_ui.urls")),
]
