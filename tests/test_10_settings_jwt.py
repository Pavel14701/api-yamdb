"""Тесты конфигурации окружения (валидатора) и контракта /auth/token/.

Контракт проверяем по схеме Token из static/redoc.yaml: ответ
токен-эндпоинта — объект с единственным полем token.
"""

from datetime import timedelta
from http import HTTPStatus

import pytest
from django.core.exceptions import ImproperlyConfigured
from rest_framework_simplejwt.tokens import AccessToken

from api_yamdb import settings as project_settings
from users.codes import generate_confirmation_code, hash_confirmation_code
from users.models import User

URL_TOKEN = '/api/v1/auth/token/'


def _make_user_with_code() -> tuple[User, str]:
    """Создаёт пользователя и возвращает его с исходным кодом."""
    user = User.objects.create_user(username='tk', email='tk@yamdb.fake')
    code = generate_confirmation_code()
    user.confirmation_code = hash_confirmation_code(code)
    user.save(update_fields=('confirmation_code',))
    return user, code


class Test10EnvValidator:
    """Fail-fast валидация небезопасных настроек вне DEBUG."""

    # Безопасные значения для НЕцелевого параметра в каждом кейсе:
    # без изоляции небезопасные значения маскируют друг друга
    # (проверка упадёт на первом же, и кейс не проверит своё).
    SAFE_ENV = {
        'SECRET_KEY': 'x' * 50,
        'ALLOWED_HOSTS': ('api.yamdb.example',),
        'DEFAULT_FROM_EMAIL': 'prod@yamdb.example',
    }

    @pytest.mark.parametrize(
        'unsafe_attr, unsafe_value',
        [
            ('SECRET_KEY', project_settings.DEV_INSECURE_SECRET_KEY),
            ('SECRET_KEY', ''),
            ('SECRET_KEY', '   '),
            ('SECRET_KEY', 'too-short-key'),
            ('ALLOWED_HOSTS', ('*',)),
            ('ALLOWED_HOSTS', ()),
            ('DEFAULT_FROM_EMAIL', 'noreply@yamdb.fake'),
        ],
        ids=[
            'default-secret-key',
            'empty-secret-key',
            'blank-secret-key',
            'weak-secret-key',
            'wildcard-hosts',
            'empty-hosts',
            'default-from-email',
        ],
    )
    def test_unsafe_value_rejected_outside_debug(
        self, monkeypatch, unsafe_attr, unsafe_value
    ):
        """Вне DEBUG небезопасное значение запрещено при безопасных остальных."""
        monkeypatch.setattr(project_settings, 'DEBUG', False)
        for attr, value in self.SAFE_ENV.items():
            if attr != unsafe_attr:
                monkeypatch.setattr(project_settings, attr, value)
        monkeypatch.setattr(project_settings, unsafe_attr, unsafe_value)

        with pytest.raises(ImproperlyConfigured):
            project_settings.validate_environment()

    def test_no_checks_in_debug(self, monkeypatch):
        """В DEBUG небезопасные значения не мешают запуску."""
        monkeypatch.setattr(project_settings, 'DEBUG', True)
        monkeypatch.setattr(
            project_settings,
            'SECRET_KEY',
            project_settings.DEV_INSECURE_SECRET_KEY,
        )
        monkeypatch.setattr(project_settings, 'ALLOWED_HOSTS', ('*',))

        project_settings.validate_environment()  # не поднимает

    def test_env_bool_parsing(self, monkeypatch):
        """_env_bool распознаёт true-значения без зависимости от регистра."""
        for truthy in ('1', 'true', 'Yes', 'ON'):
            monkeypatch.setenv('VALIDATOR_TEST_FLAG', truthy)
            assert project_settings._env_bool('VALIDATOR_TEST_FLAG', False)
        monkeypatch.setenv('VALIDATOR_TEST_FLAG', 'off')
        assert not project_settings._env_bool('VALIDATOR_TEST_FLAG', True)
        monkeypatch.delenv('VALIDATOR_TEST_FLAG', raising=False)
        assert project_settings._env_bool('VALIDATOR_TEST_FLAG', True)


@pytest.mark.django_db
class Test10TokenContract:
    """/auth/token/: контракт по схеме Token из документации."""

    def test_response_contains_only_token_field(self, client):
        _, code = _make_user_with_code()
        response = client.post(
            URL_TOKEN,
            {'username': 'tk', 'confirmation_code': code},
        )

        assert response.status_code == HTTPStatus.OK, (
            'Вход с валидным кодом должен возвращать 200.'
        )
        assert set(response.json()) == {'token'}, (
            'Схема Token документации: единственное поле token.'
        )

    def test_wrong_code_returns_400(self, client):
        _make_user_with_code()
        response = client.post(
            URL_TOKEN,
            {'username': 'tk', 'confirmation_code': 'wrong-code'},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST, (
            'Неверный код подтверждения должен возвращать 400.'
        )

    def test_unknown_user_returns_404(self, client):
        response = client.post(
            URL_TOKEN,
            {'username': 'ghost', 'confirmation_code': 'any'},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND, (
            'Неизвестный пользователь должен возвращать 404.'
        )


@pytest.mark.django_db
class Test10JwtLifetime:
    """SIMPLE_JWT: явный срок жизни access-токена применился."""

    def test_access_token_expires_in_one_day(self):
        user = User.objects.create_user(username='lt', email='lt@yamdb.fake')

        token = AccessToken.for_user(user)

        lifetime_seconds = token.payload['exp'] - token.payload['iat']
        assert lifetime_seconds == int(timedelta(days=1).total_seconds()), (
            'Access-токен должен жить сутки (не дефолтные 5 минут).'
        )
