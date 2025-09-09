from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat_view, name='chat'),
    path('chat/send-question/', views.send_question, name='send_question'),
]
