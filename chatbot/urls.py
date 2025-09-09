from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("chat/", views.chat_view, name="chat"),
    path("api/send/", views.api_send, name="api_send"),
    path("api/progress/", views.api_progress, name="api_progress"),
]