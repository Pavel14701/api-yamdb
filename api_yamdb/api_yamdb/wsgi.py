"""WSGI config for YaMDb project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_yamdb.settings')

# Fail-fast проверка окружения (небезопасные дефолты вне DEBUG).
# Импорт после setdefault обязателен: settings читает окружение
# при импорте — поэтому noqa: E402.
from api_yamdb.settings import validate_environment  # noqa: E402

validate_environment()

application = get_wsgi_application()
