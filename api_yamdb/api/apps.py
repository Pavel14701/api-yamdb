"""Конфигурация приложения api."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Настройки приложения с логикой API."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = 'API'
