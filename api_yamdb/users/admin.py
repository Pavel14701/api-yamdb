"""Регистрация модели пользователя в админ-зоне."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class YamdbUserAdmin(UserAdmin[User]):
    """Настройка отображения пользователей в админ-зоне."""

    list_display = (
        'username',
        'email',
        'role',
        'first_name',
        'last_name',
    )
    search_fields = ('username', 'email')
    list_filter = ('role',)
    fieldsets = tuple(UserAdmin.fieldsets or ()) + (
        ('YaMDb', {'fields': ('role', 'bio', 'confirmation_code')}),
    )
