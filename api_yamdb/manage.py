#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Команды первоначальной настройки и разработки: работают на чистом
# клоне без переменных окружения — документированный `migrate` не
# должен падать до окончания настройки (замечание ревью). Сервисные
# точки входа (runserver, wsgi.py, asgi.py) валидацию проходят как раньше.
SETUP_COMMANDS = frozenset({
    'check',
    'collectstatic',
    'createsuperuser',
    'dbshell',
    'load_csv',
    'makemigrations',
    'migrate',
    'shell',
    'showmigrations',
    'sqlmigrate',
    'test',
})


def main() -> None:
    """Запускает административные команды Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_yamdb.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Fail-fast проверка окружения (небезопасные дефолты вне DEBUG) —
    # кроме команд настройки (см. SETUP_COMMANDS).
    if len(sys.argv) < 2 or sys.argv[1] not in SETUP_COMMANDS:
        from api_yamdb.settings import validate_environment

        validate_environment()
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
