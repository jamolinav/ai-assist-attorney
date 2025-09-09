from django.urls import path
from .views import MCPEndpoint

urlpatterns = [
    path('conversation/', MCPEndpoint.as_view(), name='mcp_endpoint'),
]
