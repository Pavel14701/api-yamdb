"""Сериализаторы для регистрации, токенов и пользователей."""

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from users.models import User
from users.utils import hash_confirmation_code

UserModel = get_user_model()

FORBIDDEN_USERNAME = 'me'
MSG_FORBIDDEN_USERNAME = 'Использовать имя "me" в качестве username запрещено.'
MSG_WRONG_CONFIRMATION_CODE = 'Неверный код подтверждения.'


class SignUpSerializer(serializers.Serializer[dict[str, Any]]):
    """Сериализатор самостоятельной регистрации пользователя.

    Принимает только email и username — пароль при регистрации
    не используется, вход выполняется по коду подтверждения.
    """

    email = serializers.EmailField(max_length=254)
    username = serializers.RegexField(
        regex=r'^[\w.@+-]+\Z',
        max_length=150,
    )

    def validate_username(self, value: str) -> str:
        """Запрещает регистрацию с зарезервированным username 'me'.

        Имя 'me' используется эндпоинтом /users/me/ для обращения
        к собственному профилю пользователя.
        """
        if value.lower() == FORBIDDEN_USERNAME:
            raise serializers.ValidationError(MSG_FORBIDDEN_USERNAME)
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Проверяет конфликты с уже зарегистрированными пользователями.

        - username занят другим email — ошибка по полю username;
        - email занят другим username — ошибка по полю email;
        - повторная регистрация с теми же данными разрешена
          (пользователю будет выслан новый код подтверждения).
        """
        username = data['username']
        email = data['email']
        if UserModel.objects.filter(username=username).exists():
            user = UserModel.objects.get(username=username)
            if user.email != email:
                raise serializers.ValidationError(
                    {'username': 'Такой username уже занят.'}
                )
        elif User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {'email': 'Такой email уже зарегистрирован.'}
            )
        return data


class GetTokenSerializer(serializers.Serializer[dict[str, Any]]):
    """Сериализатор получения JWT-токена по коду подтверждения."""

    username = serializers.CharField(max_length=150)
    confirmation_code = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Проверяет пользователя и код подтверждения.

        Неизвестный username — 404, неверный confirmation_code — 400.
        В проверку передаётся пользователь, чтобы вьюха могла
        выдать для него токен.
        """
        try:
            user = UserModel.objects.get(username=data['username'])
        except User.DoesNotExist:
            raise NotFound('Пользователь не найден.') from None
        code_hash = hash_confirmation_code(data['confirmation_code'])
        if user.confirmation_code != code_hash:
            raise serializers.ValidationError(MSG_WRONG_CONFIRMATION_CODE)
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer[User]):
    """Сериализатор пользователей для админских эндпоинтов /users/.

    Валидация полей (длины, паттерн username, уникальность
    username и email, допустимые значения role) наследуется
    из модели User.
    """

    class Meta:
        """Настройки сериализатора."""

        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'bio',
            'role',
        )


class UserMeSerializer(UserSerializer):
    """Сериализатор эндпоинта /users/me/.

    Отдаёт тот же набор полей, что и UserSerializer, но роль
    пользователь изменить не может — это прерогатива админа.
    """

    class Meta(UserSerializer.Meta):
        """Наследует поля UserSerializer, роль — только чтение."""

        read_only_fields = ('role',)
