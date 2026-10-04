"""Модель пользователя проекта YaMDb."""

import re

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils.regex_helper import _lazy_re_compile

from api_yamdb.constants import (
    MAX_LENGTH_CONFIRMATION_CODE,
    MAX_LENGTH_EMAIL,
    MAX_LENGTH_ROLE,
    MAX_LENGTH_USERNAME,
)

# Валидатор username: встроенная регулярка Django (см.
# django.contrib.auth.validators.UnicodeUsernameValidator) плюс
# запрет зарезервированного имени "me" — один объединяющий валидатор.
USERNAME_REGEX = r'^(?!me\Z)[\w.@+-]+\Z'
validate_username = RegexValidator(
    _lazy_re_compile(USERNAME_REGEX, re.IGNORECASE),
    message=(
        'Username: допускаются буквы, цифры и символы @/./+/-/_ ;'
        ' имя "me" зарезервировано и запрещено.'
    ),
    code='invalid_username',
)


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

    username = models.CharField(
        'имя пользователя',
        max_length=MAX_LENGTH_USERNAME,
        unique=True,
        validators=(validate_username,),
        error_messages={
            'unique': 'Пользователь с таким именем уже существует.',
        },
    )
    email = models.EmailField(
        'email адрес',
        unique=True,
        max_length=MAX_LENGTH_EMAIL,
    )
    role = models.CharField(
        'роль',
        max_length=MAX_LENGTH_ROLE,
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
        max_length=MAX_LENGTH_CONFIRMATION_CODE,
        blank=True,
        help_text='Хранится в виде хэша; исходный код уходит на email.',
    )

    class Meta:
        """Настройки отображения модели."""

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

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
