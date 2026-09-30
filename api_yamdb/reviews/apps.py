"""Конфигурация приложения reviews (произведения, отзывы, комментарии)."""

from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    """Настройки приложения с моделями контента YaMDb."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reviews'
    verbose_name = 'Отзывы и произведения'
