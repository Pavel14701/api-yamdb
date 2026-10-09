# YaMDb — сбор отзывов на произведения

[![CI](https://github.com/Pavel14701/api-yamdb/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Pavel14701/api-yamdb/actions/workflows/ci.yml)

YaMDb собирает отзывы пользователей на произведения: книги, фильмы и музыку.
Произведения делятся на категории («Книги», «Фильмы», «Музыка») и получают
рейтинг — среднее арифметическое оценок из отзывов, округлённое до целого.
На одно произведение можно оставить несколько отзывов и комментировать чужие.

## Использованные технологии

**Рантайм:**

- [Python 3.12](https://docs.python.org/3/) — язык проекта
- [Django 5.1](https://docs.djangoproject.com/en/5.1/) — веб-фреймворк (ORM, миграции, админка, management-команды)
- [Django REST Framework 3.15](https://www.django-rest-framework.org/) — REST API (вьюсеты, сериализаторы, права, пагинация)
- [SimpleJWT 5.4](https://django-rest-framework-simplejwt.readthedocs.io/) — аутентификация по JWT-токену (access на 24 часа)
- [django-filter 25.1](https://django-filter.readthedocs.io/) — фильтрация произведений (категория, жанр, год, имя)
- [SQLite3](https://www.sqlite.org/) — база данных

**Качество кода и тесты:**

- [pytest 8.3](https://docs.pytest.org/) + [pytest-django](https://pytest-django.readthedocs.io/) — 110 тестов (курсовые + юнит-тесты сервисного слоя и настроек)
- [ruff](https://docs.astral.sh/ruff/) — основной линтер (B, C4, D/pydocstyle, E, F, I, N, SIM, UP, W)
- [flake8 7.1](https://flake8.pycqa.org/) — линтер (PEP 8, `max-complexity=10`)
- [mypy](https://mypy-lang.org/) — строгая типизация (`strict`, плагины django-stubs / djangorestframework-stubs)

**Инфраструктура:**

- [GitHub Actions](https://docs.github.com/actions) — CI: линтеры + pytest на push и PR в `main`/`develop` (переиспользуемый workflow + джобы по участникам и сквозная джоба `infra`)

Зависимости: рантайм — `requirements.txt`; инструменты разработки — группа `dev` в `pyproject.toml`.


## Возможности API

| Ресурс | Что умеет |
|---|---|
| `auth/` | получение JWT-токена, регистрация |
| `users/` | профиль, роли (user/moderator/admin), управление админом |
| `titles/` | произведения с фильтрами по категории, жанру, году, имени |
| `categories/` | категории произведений |
| `genres/` | жанры произведений |
| `titles/{id}/reviews/` | отзывы со score 1–10 и рейтингом произведения |
| `titles/{id}/reviews/{id}/comments/` | комментарии к отзывам |

Права: аноним — только чтение; автор отзыва/комментария, модератор и
администратор — запись/удаление по иерархии ролей.

## Примеры запросов

Базовый URL: `http://127.0.0.1:8000/api/v1/`

### 1. Регистрация и получение токена

```bash
# регистрация — на почту придёт confirmation_code
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{"username": "new_user", "email": "user@example.com"}'

# обмен confirmation_code на JWT-токен
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "new_user", "confirmation_code": "<код из письма>"}'
```

Ответ содержит `token` — далее передаём его в заголовке:
`Authorization: Bearer <token>`.

### 2. Чтение (доступно и без токена)

```bash
# список произведений с фильтрами (категория, жанр, год, имя)
curl "http://127.0.0.1:8000/api/v1/titles/?genre=comedy&year=2019&name=bohem"

# категории и жанры
curl http://127.0.0.1:8000/api/v1/categories/
curl http://127.0.0.1:8000/api/v1/genres/

# отзывы и комментарии к произведению
curl http://127.0.0.1:8000/api/v1/titles/1/reviews/
curl http://127.0.0.1:8000/api/v1/titles/1/reviews/1/comments/
```

### 3. Запись (нужен токен)

```bash
# свой профиль
curl http://127.0.0.1:8000/api/v1/users/me/ \
  -H "Authorization: Bearer <token>"

# отзыв с оценкой 1–10 (только аутентифицированный)
curl -X POST http://127.0.0.1:8000/api/v1/titles/1/reviews/ \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"text": "Отличный фильм!", "score": 9}'

# комментарий к отзыву
curl -X POST http://127.0.0.1:8000/api/v1/titles/1/reviews/1/comments/ \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"text": "Согласен, шедевр"}'
```

## Документация

Полное описание эндпоинтов — Redoc: `http://127.0.0.1:8000/redoc/`

## Запуск

```bash
git clone https://github.com/Pavel14701/api-yamdb.git
cd api-yamdb
python -m venv venv
venv\Scripts\activate           # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

cd api_yamdb
python manage.py migrate
python manage.py load_csv       # импорт данных из static/data/*.csv

# Для runserver (в отличие от migrate/load_csv) вне DEBUG нужны
# переменные окружения — см. .env.example. Для локальной разработки
# достаточно включить DEBUG:
set DEBUG=true                  # PowerShell: $env:DEBUG='true'; bash: export DEBUG=true
python manage.py runserver
```

После `load_csv` база наполнена демо-данными: 5 пользователей, 32 произведения,
15 жанров, 3 категории, 72 отзыва, комментарии (идемпотентно — повторный
запуск не создаёт дубликаты).

## Тесты и CI

```bash
pytest            # 110 тестов
ruff check .      # линтер
flake8            # линтер (PEP8)
mypy              # строгая типизация
```

GitHub Actions запускает все четыре проверки на push и PR в `main`/`develop`:
доменные джобы участников (матчатся на ветку автора) плюс сквозная джоба
`infra` для тестов без доменной принадлежности.

## Команда

| Участник | Что сделал |
|---|---|
| **Павел Кутья** (тимлид) | инфраструктура и интеграция: CI/CD (диспетчер + reusable workflow: ruff/flake8/mypy strict/pytest); ревью и слияние всех веток, разрешение конфликтов; багфиксы (запрет анонимного POST, 405 на PUT, django-filter в requirements); hotfix моделей и миграций reviews; типизация views/serializers под mypy strict; тесты-ТЗ импорта CSV (10 тестов) и фикс pub_date в импорте; финальная сборка `develop` → `master` |
| **Карина Савина** (dev) | модели Category, Genre, Title + миграции; все вьюсеты проекта (category → genre → title → reviews → comments) и консолидация всех сериализаторов в `api/serializers.py`; её версия вошла в `develop` (CI зелёный); |
| **Елена Тишина** (dev) | модели Review, Comment + права доступа; маршрутизация (`reviews/urls.py`); аннотация рейтинга произведения (Avg); management-команда `load_csv` — импорт 7 CSV-файлов с `update_or_create` и толерантностью к битым строкам (задача перераспределена с Карины); |

## Автор

Проект выполнен в рамках учебного модуля Яндекса (командная работа).

- **Павел Кутья** (тимлид) — [github.com/Pavel14701](https://github.com/Pavel14701)
- **Карина Савина** (dev)
- **Елена Тишина** (dev)
