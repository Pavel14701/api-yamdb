# YaMDb — сбор отзывов на произведения

[![CI](https://github.com/Pavel14701/api-yamdb/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Pavel14701/api-yamdb/actions/workflows/ci.yml)

YaMDb собирает отзывы пользователей на произведения: книги, фильмы и музыку.
Произведения делятся на категории («Книги», «Фильмы», «Музыка») и получают
рейтинг — среднее арифметическое оценок из отзывов, округлённое до целого.
На одно произведение можно оставить несколько отзывов и комментировать чужие.

## Стек

- Python 3.12, Django 5.1, Django REST Framework 3.15
- SimpleJWT (аутентификация), djoser (регистрация), django-filter
- SQLite3, pytest, ruff / flake8 / mypy (strict)

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
python manage.py runserver
```

После `load_csv` база наполнена демо-данными: 5 пользователей, 32 произведения,
15 жанров, 3 категории, 72 отзыва, комментарии (идемпотентно — повторный
запуск не создаёт дубликаты).

## Тесты и CI

```bash
pytest            # 90 тестов
ruff check .      # линтер
flake8            # линтер (PEP8)
mypy              # строгая типизация
```

GitHub Actions запускает все четыре проверки на push и PR в `main`/`develop`.
Каждая джоба матчится на ветку автора (`contains(head_ref, ...)`).

## Команда

| Участник | Что сделал |
|---|---|
| **Павел Кутья** (тимлид) | инфраструктура и интеграция: CI/CD (диспетчер + reusable workflow: ruff/flake8/mypy strict/pytest); ревью и слияние всех веток, разрешение конфликтов; багфиксы (запрет анонимного POST, 405 на PUT, django-filter в requirements); hotfix моделей и миграций reviews; типизация views/serializers под mypy strict; тесты-ТЗ импорта CSV (10 тестов) и фикс pub_date в импорте; финальная сборка `develop` → `master` |
| **Карина Савина** (dev) | модели Category, Genre, Title + миграции; все вьюсеты проекта (category → genre → title → reviews → comments) и консолидация всех сериализаторов в `api/serializers.py`; её версия вошла в `develop` (CI зелёный); |
| **Елена Тишина** (dev) | модели Review, Comment + права доступа; маршрутизация (`reviews/urls.py`); аннотация рейтинга произведения (Avg); management-команда `load_csv` — импорт 7 CSV-файлов с `update_or_create` и толерантностью к битым строкам (задача перераспределена с Карины); |
