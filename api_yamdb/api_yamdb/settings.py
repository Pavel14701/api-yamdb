"""Настройки проекта YaMDb (Django settings).

Секреты и режимные параметры читаются из переменных окружения
(stdlib os, без сторонних загрузчиков). Значения по умолчанию
пригодны для разработки; запуск вне DEBUG с небезопасными
значениями запрещён функцией validate_environment() — её вызывают
точки входа (manage.py, wsgi.py, asgi.py). Список переменных —
в .env.example.
"""

import os
from datetime import timedelta
from pathlib import Path
from typing import Final

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    """Читает булеву переменную окружения ('1'/'true'/'yes'/'on')."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_list(name: str, default: str) -> tuple[str, ...]:
    """Читает список значений через запятую из переменной окружения."""
    raw = os.environ.get(name)
    if raw is None:
        raw = default
    return tuple(item.strip() for item in raw.split(',') if item.strip())


# Ключ по умолчанию — только для разработки: вне DEBUG валидатор
# его отвергнет (см. конец модуля).
DEV_INSECURE_SECRET_KEY = 'django-insecure-dev-only-key-yamdb'
# Минимальная длина секретного ключа вне DEBUG: отсекает короткие
# «вручную придуманные» ключи — угаданный ключ позволяет подделывать
# подписанные им JWT-токены (замечание ревью).
MIN_SECRET_KEY_LENGTH: Final = 50
# Эвристика «набранного руками» ключа: маркеры проверяются по
# нормализованному виду (нижний регистр, только буквы и цифры),
# разнообразие — по числу РАЗЛИЧНЫХ символов: случайный ключ из
# secrets.token_urlsafe(64) даёт 30+ разных символов, фраза,
# придуманная человеком, — обычно меньше (замечание ревью:
# длина сама по себе не делает ключ непредсказуемым).
PREDICTABLE_SECRET_MARKERS = (
    'djangoinsecure',
    'secret',
    'password',
    'passwd',
    'changeme',
    'placeholder',
    'qwerty',
    'example',
)
MIN_SECRET_ALPHABET: Final = 30
SECRET_KEY = os.environ.get('SECRET_KEY', DEV_INSECURE_SECRET_KEY)
# Дефолт False: незаданный DEBUG не должен включать отладку.
DEBUG = _env_bool('DEBUG', False)
ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS', '*')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'users',
    'api',
    'reviews',
]

# Кастомная модель пользователя. Должна быть задана ДО первой
# миграции проекта.
AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'api_yamdb.urls'

TEMPLATES_DIR = BASE_DIR / 'templates'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'api_yamdb.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'

STATICFILES_DIRS = ((BASE_DIR / 'static/'),)

# Настройки DRF: аутентификация по JWT-токену, пагинация списков.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# Настройки почты для отладки: письма печатаются в консоль,
# из них берётся confirmation_code для получения токена.
# Валидатор запрещает дефолтный отправитель вне DEBUG.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@yamdb.fake')

# Явные сроки жизни JWT вместо дефолтов simplejwt (access всего
# 5 минут). По документации ресурс auth выдаёт один access-токен
# (схема Token: единственное поле token), refresh-токены не
# используются — параметры ниже заданы для полноты конфигурации.
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# --- Валидация окружения (fail-fast) --------------------------------------
# Запуск вне DEBUG с небезопасными значениями — ошибка конфигурации:
# проект отказывается стартовать, а не молча работает небезопасно.
# Вызывается из точек входа (manage.py, wsgi.py, asgi.py) после
# чтения окружения; тесты валидатор не вызывают (им прод не нужен).


def _is_predictable_secret(key: str) -> bool:
    """Эвристика «набранного руками» (угадываемого) ключа.

    True, если в нормализованном ключе есть известный маркер
    или разнообразие символов ниже MIN_SECRET_ALPHABET — случайный
    ключ из secrets.token_urlsafe(64) не попадает ни под один из
    признаков (замечание ревью: проверки только длины мало).
    """
    normalized = ''.join(ch for ch in key.lower() if ch.isalnum())
    if any(marker in normalized for marker in PREDICTABLE_SECRET_MARKERS):
        return True
    return len(set(key)) < MIN_SECRET_ALPHABET


def validate_environment() -> None:
    """Проверяет безопасность настроек при DEBUG=False.

    Поднимает ImproperlyConfigured, если вне отладочного режима
    остались пустые, дефолтные или слабые значения секретов.
    """
    if DEBUG:
        return
    if not SECRET_KEY.strip():
        raise ImproperlyConfigured(
            'SECRET_KEY не может быть пустым при DEBUG=False '
            '(см. .env.example).'
        )
    if SECRET_KEY == DEV_INSECURE_SECRET_KEY:
        raise ImproperlyConfigured(
            'SECRET_KEY должен быть задан переменной окружения '
            'при DEBUG=False (см. .env.example).'
        )
    if len(SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
        raise ImproperlyConfigured(
            f'SECRET_KEY короче {MIN_SECRET_KEY_LENGTH} символов '
            'запрещён при DEBUG=False: слабый ключ позволяет '
            'подделывать JWT. Сгенерируйте, например: '
            'python -c "import secrets; print(secrets.token_urlsafe(64))".'
        )
    if _is_predictable_secret(SECRET_KEY):
        raise ImproperlyConfigured(
            'SECRET_KEY при DEBUG=False должен быть криптографически '
            'случайным: угадываемый (набранный руками) ключ позволяет '
            'подделывать JWT. Сгенерируйте, например: '
            'python -c "import secrets; print(secrets.token_urlsafe(64))".'
        )
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS при DEBUG=False — непустой список хостов "
            "через запятую ('*' запрещён: без хостов API недоступен, "
            'с wildcard запросы отвергаются или опасны).'
        )
    if DEFAULT_FROM_EMAIL == 'noreply@yamdb.fake':
        raise ImproperlyConfigured(
            'DEFAULT_FROM_EMAIL должен быть задан при DEBUG=False.'
        )
