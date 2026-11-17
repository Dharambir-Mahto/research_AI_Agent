from django.urls import path
from . import views

app_name = "research_ui"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/chat/", views.chat_api, name="chat_api"),
    path("api/reports/", views.reports_api, name="reports_api"),
    path(
        "api/reports/download/<path:relpath>",
        views.download_report,
        name="download_report",
    ),
    path(
        "api/reports/preview/<path:relpath>",
        views.preview_report,
        name="preview_report",
    ),
    path("api/status/", views.status_api, name="status_api"),
    path("api/reset/", views.reset_api, name="reset_api"),
    path("api/conversations/", views.conversations_list_api, name="conversations_list"),
    path("api/conversations/clear/", views.conversations_clear_api, name="conversations_clear"),
    path("api/conversations/<str:conv_id>/", views.conversation_detail_api, name="conversation_detail"),
    path("api/conversations/<str:conv_id>/delete/", views.conversation_delete_api, name="conversation_delete"),
]
