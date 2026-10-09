"""Юнит-тесты сервисного слоя и чистой логики (не HTTP).

Покрывают напрямую то, что функциональные тесты курса задевают
только через эндпоинты: signup_user, ретраи доставки письма,
parse_row, with_rating.
"""

from unittest.mock import patch

import pytest
from django.db import transaction as db_transaction

from reviews.management.exceptions import FieldParseError, MissingColumnError
from reviews.management.parsing import parse_row
from reviews.models import Category, Review, Title
from users.codes import hash_confirmation_code
from users.exceptions import EmailDeliveryError
from users.models import User
from users.services import (
    EMAIL_MAX_ATTEMPTS,
    send_confirmation_code,
    signup_user,
)


@pytest.mark.django_db
class Test09SignupService:
    """signup_user: создание, хэширование кода, регенерация."""

    USERNAME = 'neo'
    EMAIL = 'neo@example.com'

    def test_signup_creates_user_with_hashed_code(self):
        user, code = signup_user(self.USERNAME, self.EMAIL)

        assert User.objects.filter(username=self.USERNAME).exists(), (
            'signup_user должен создать пользователя.'
        )
        assert user.confirmation_code == hash_confirmation_code(code), (
            'В БД должен храниться хэш кода, а не исходный код.'
        )
        assert user.confirmation_code != code, (
            'Исходный код не должен сохраняться в БД в открытом виде.'
        )

    def test_repeat_signup_regenerates_code(self):
        _, first_code = signup_user(self.USERNAME, self.EMAIL)
        _, second_code = signup_user(self.USERNAME, self.EMAIL)

        assert first_code != second_code, (
            'Повторный signup должен генерировать новый код.'
        )
        user = User.objects.get(username=self.USERNAME)
        assert user.confirmation_code == hash_confirmation_code(second_code), (
            'В БД должен остаться хэш последнего кода.'
        )

    def test_atomic_rollback_keeps_user_with_code(self):
        """Сбой после get_or_create откатывает и создание пользователя."""
        with db_transaction.atomic():
            with patch(
                'users.services.hash_confirmation_code',
                side_effect=RuntimeError('boom'),
            ):
                with pytest.raises(RuntimeError):
                    signup_user(self.USERNAME, self.EMAIL)
            # Вложенный atomic нужен, чтобы RuntimeError пометил
            # транзакцию теста; проверяем результат после выхода.
        assert not User.objects.filter(username=self.USERNAME).exists(), (
            'Сбой записи кода должен откатывать создание пользователя.'
        )


@pytest.mark.django_db
class Test09EmailRetry:
    """send_confirmation_code: ретраи и EmailDeliveryError."""

    def test_retries_until_success(self):
        failures = [ConnectionError('down'), ConnectionError('down'), None]
        with patch(
            'users.services._send_code_email',
            side_effect=failures,
        ) as send_mock, patch('users.services.time.sleep'):
            user = User(username='tr', email='tr@example.com')
            send_confirmation_code(user, 'code123')

        assert send_mock.call_count == 3, (
            'После двух сетевых сбоев письмо должно уйти с третьей попытки.'
        )

    def test_raises_after_exhausted_attempts(self):
        with patch(
            'users.services._send_code_email',
            side_effect=ConnectionError('down'),
        ) as send_mock, patch('users.services.time.sleep'):
            user = User(username='ex', email='ex@example.com')
            with pytest.raises(EmailDeliveryError) as exc_info:
                send_confirmation_code(user, 'code123')

        assert send_mock.call_count == EMAIL_MAX_ATTEMPTS, (
            'Должно быть сделано ровно EMAIL_MAX_ATTEMPTS попыток.'
        )
        assert exc_info.value.attempts == EMAIL_MAX_ATTEMPTS
        assert exc_info.value.__cause__ is not None, (
            'Исходная ошибка сети должна быть доступна через __cause__.'
        )


class Test09ParseRow:
    """parse_row: чистый парсинг без БД."""

    def test_happy_path_casts_numerics(self):
        row = {'id': '1', 'name': 'Книга', 'year': '2000'}
        result = parse_row(row, ('id', 'name', 'year'))

        assert result == {'name': 'Книга', 'year': 2000}, (
            'Числовые поля должны приводиться к int, id — пропускаться.'
        )

    def test_csv_field_alias(self):
        result = parse_row({'category': '3'}, ('category_id',))

        assert result == {'category_id': 3}, (
            'Колонка CSV `category` должна читаться в поле `category_id`.'
        )

    def test_missing_column(self):
        with pytest.raises(MissingColumnError) as exc_info:
            parse_row({'id': '1'}, ('id', 'author_id'))

        # В исключении — имя колонки CSV (по алиасу), а не поля модели.
        assert exc_info.value.column == 'author', (
            'В исключении должно быть имя отсутствующей колонки CSV.'
        )

    def test_bad_int_raises_field_parse_error(self):
        with pytest.raises(FieldParseError):
            parse_row({'id': '1', 'year': 'две тыщи'}, ('id', 'year'))


@pytest.mark.django_db
class Test09TitleRating:
    """with_rating: аннотация рейтинга и None без отзывов."""

    @staticmethod
    def _make_title() -> Title:
        category = Category.objects.create(name='Книги', slug='books')
        return Title.objects.create(
            name='Тестовое произведение',
            year=2020,
            category=category,
        )

    def test_rating_is_average(self):
        title = self._make_title()
        authors = [
            User.objects.create_user(username=f'r{i}', email=f'r{i}@x.io')
            for i in range(2)
        ]
        for i, author in enumerate(authors):
            Review.objects.create(
                title=title,
                text=f'Отзыв {i}',
                author=author,
                score=5 + i * 2,
            )

        rated = Title.objects.with_rating().get(pk=title.pk)
        assert rated.rating == 6, (
            'Рейтинг должен быть округлённым средним score отзывов.'
        )

    def test_rating_is_none_without_reviews(self):
        title = self._make_title()

        rated = Title.objects.with_rating().get(pk=title.pk)
        assert rated.rating is None, (
            'У произведения без отзывов рейтинг должен быть None.'
        )
