"""Модель пользователя проекта YaMDb."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Кастомная модель пользователя.

    Расширяет стандартную модель Django полями, которые требуются
    по спецификации YaMDb: роль, биография и код подтверждения.
    Код подтверждения отправляется на email при регистрации
    и используется для получения JWT-токена.
    """

    USER = 'user'
    MODERATOR = 'moderator'
    ADMIN = 'admin'

    ROLE_CHOICES = (
        (USER, 'Пользователь'),
        (MODERATOR, 'Модератор'),
        (ADMIN, 'Администратор'),
    )

    email = models.EmailField(
        'email адрес',
        unique=True,
        max_length=254,
    )
    role = models.CharField(
        'роль',
        max_length=30,
        choices=ROLE_CHOICES,
        default=USER,
        help_text='Роль нового пользователя по умолчанию — "user".',
    )
    bio = models.TextField(
        'биография',
        blank=True,
    )
    confirmation_code = models.CharField(
        'код подтверждения',
        max_length=128,
        blank=True,
        help_text='Хранится в виде хэша; исходный код уходит на email.',
    )

    class Meta:
        """Настройки отображения модели."""

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('id',)

    def __str__(self) -> str:
        """Возвращает username пользователя."""
        return self.username

    @property
    def is_admin(self) -> bool:
        """Является ли пользователь администратором.

        Суперпользователь всегда считается администратором,
        даже если его роль в базе изменена.
        """
        return self.role == self.ADMIN or self.is_superuser
