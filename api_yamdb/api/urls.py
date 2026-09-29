"""Маршруты API v1 (приложение api)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api import views

router_v1 = DefaultRouter()
router_v1.register('users', views.UserViewSet, basename='users')

urlpatterns = [
    path('auth/signup/', views.signup, name='signup'),
    path('auth/token/', views.obtain_token, name='token'),
    path('', include(router_v1.urls)),
]
