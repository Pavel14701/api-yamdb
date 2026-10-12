"""Маршруты пользователей и аутентификации (приложение users)."""

# Требования тестов, если положить в апи регрессия

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.api.v1 import views

users_router = DefaultRouter()
users_router.register('users', views.UserViewSet, basename='users')

auth_urls = [
    path('signup/', views.signup, name='signup'),
    path('token/', views.obtain_token, name='token'),
]

urlpatterns = [
    path('auth/', include(auth_urls)),
    path('', include(users_router.urls)),
]
