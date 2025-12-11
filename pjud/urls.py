"""
URL configuration for pjud project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets
from django.conf import settings
from django.conf.urls.static import static
import os
from django.contrib.auth import views as auth_views
#from chatbot_app.views import register_user, crear_password


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'is_staff']

# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

WEBSITE_SITE_NAME = '' if os.environ.get('WEBSITE_SITE_NAME') is None else os.environ.get('WEBSITE_SITE_NAME')

urlpatterns = [
    path('admin/', admin.site.urls),
    # Add your app URLs here
    path('civil/', include('civil.urls')),
    path('chatbot/', include('chatbot.urls')),
    #path('chatbot/', include('chatbot_app.urls')),
    path('mcp/', include('mcp_app.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    #path('accounts/register_user/', register_user, name='register_user'),
    #path("accounts/crear_password/", crear_password, name="crear_password"),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)