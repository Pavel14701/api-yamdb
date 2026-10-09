"""Юнит-тесты сервисного слоя и чистой логики (не HTTP).

Покрывают напрямую то, что функциональные тесты курса задевают
только через эндпоинты: signup_user (включая гонки параллельных
регистраций), ретраи доставки письма, parse_row, with_rating,
толерантность _import_genre_titles к битым строкам.
"""

import io
import smtplib
from unittest.mock import patch

import pytest
from django.core import mail
from django.db import IntegrityError, transaction as db_transaction
from rest_framework.exceptions import ValidationError

from reviews.management.commands.load_csv import Command as LoadCsvCommand
from reviews.management.exceptions import FieldParseError, MissingColumnError
from reviews.management.parsing import parse_row
from reviews.models import Category, Genre, Review, Title
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
    """signup_user: создание, хэширование кода, регенерация, гонки."""

    USERNAME = 'neo'
    EMAIL = 'neo@example.com'

    @staticmethod
    def _last_sent_code() -> str:
        """Код из последнего письма (locmem-бэкенд копит их в mail.outbox)."""
        return mail.outbox[-1].body.rsplit(': ', 1)[-1]

    def test_signup_creates_user_with_hashed_code(self):
        user = signup_user(self.USERNAME, self.EMAIL)

        assert User.objects.filter(username=self.USERNAME).exists(), (
            'signup_user должен создать пользователя.'
        )
        assert user.email == self.EMAIL
        assert user.confirmation_code == hash_confirmation_code(
            self._last_sent_code()
        ), 'В БД должен храниться хэш именно отправленного кода.'
        assert user.confirmation_code != self._last_sent_code(), (
            'Исходный код не должен храниться в БД в открытом виде.'
        )

    def test_repeat_signup_regenerates_code(self):
        signup_user(self.USERNAME, self.EMAIL)
        first_hash = User.objects.get(
            username=self.USERNAME
        ).confirmation_code
        signup_user(self.USERNAME, self.EMAIL)

        second_hash = User.objects.get(
            username=self.USERNAME
        ).confirmation_code
        assert first_hash != second_hash, (
            'Повторный signup должен обновлять хэш кода в БД.'
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

    @pytest.mark.django_db(transaction=True)
    def test_code_is_sent_after_commit(self):
        """Письмо уходит ПОСЛЕ коммита: хэш уже виден всем транзакциям.

        Отправка до коммита при откате оставляла бы у получателя
        «отозванный» код — его нет в БД (замечание ревью).
        TransactionTestCase: под обычным TestCase тест целиком живёт
        в atomic-обёртке, и выход из внутреннего atomic — лишь
        savepoint, коммит не проверить.
        """
        seen: dict[str, object] = {}

        def probe(email, code):
            seen['in_atomic'] = db_transaction.get_connection().in_atomic_block
            stored = User.objects.get(username=self.USERNAME)
            seen['stored_hash'] = stored.confirmation_code
            seen['expected_hash'] = hash_confirmation_code(code)

        with patch('users.services._send_code_email', side_effect=probe):
            signup_user(self.USERNAME, self.EMAIL)

        assert seen['in_atomic'] is False, (
            'Доставка кода должна выполняться после выхода из '
            'atomic-блока — иначе при откате транзакции получатель '
            'останется с кодом, которого нет в БД.'
        )
        assert seen['stored_hash'] == seen['expected_hash'], (
            'К моменту доставки хэш отправляемого кода должен быть '
            'уже закоммичен.'
        )

    def test_superseded_code_not_sent(self):
        """Перезаписанный параллельным signup код не доставляется.

        Между коммитом и доставкой другой запрос мог обновить хэш —
        наш код отозван, письмо за него отправлять нельзя.
        """
        with patch(
            'users.services._stored_confirmation_hash',
            return_value='superseded-by-parallel-signup',
        ), patch(
            'users.services._send_code_email',
        ) as send_mock:
            signup_user(self.USERNAME, self.EMAIL)

        send_mock.assert_not_called()

    def test_existing_user_with_other_email_rejected(self):
        """Аккаунт с другим email (гонка/админ) не используется."""
        User.objects.create_user(
            username=self.USERNAME, email='other@example.com'
        )

        with pytest.raises(ValidationError):
            signup_user(self.USERNAME, self.EMAIL)

    def test_email_uniqueness_race_becomes_validation_error(self):
        """Гонка уникального email — ValidationError, а не сырой 500."""
        with patch(
            'users.services.User.objects.get_or_create',
            side_effect=IntegrityError('unique email'),
        ):
            with pytest.raises(ValidationError):
                signup_user(self.USERNAME, self.EMAIL)



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

    def test_smtp_exception_is_retried(self):
        """SMTPException явно входит в ретраи, а не выходит наружу."""
        failures = [smtplib.SMTPException('relay denied'), None]
        with patch(
            'users.services._send_code_email',
            side_effect=failures,
        ) as send_mock, patch('users.services.time.sleep'):
            user = User(username='smtp', email='smtp@example.com')
            send_confirmation_code(user, 'code123')

        assert send_mock.call_count == 2, (
            'После сбоя SMTP письмо должно уйти со второй попытки.'
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

    def test_missing_numeric_cell_raises_field_parse_error(self):
        """Пустая ячейка числовой колонки (None) — FieldParseError.

        csv.DictReader отдаёт None вместо строки для отсутствующей
        ячейки; int(None) — TypeError, он тоже должен превращаться
        в перехватываемый CsvImportError, а не ронять импорт.
        """
        with pytest.raises(FieldParseError):
            parse_row({'id': '1', 'year': None}, ('id', 'year'))


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
        """Дробное среднее округляется, а не усекается.

        Оценки 5 и 8 дают среднее 6.5: корректная реализация
        вернёт 7, усекающая (int()) — 6 (замечание ревью: среднее
        6 из оценок 5 и 7 не различает trunc и round).
        """
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
                score=5 + i * 3,
            )

        rated = Title.objects.with_rating().get(pk=title.pk)
        assert rated.rating == 7, (
            'Рейтинг должен быть округлённым средним score отзывов '
            '(среднее 5 и 8 = 6.5 округляется до 7, а не усекается до 6).'
        )

    def test_rating_is_none_without_reviews(self):
        title = self._make_title()

        rated = Title.objects.with_rating().get(pk=title.pk)
        assert rated.rating is None, (
            'У произведения без отзывов рейтинг должен быть None.'
        )


@pytest.mark.django_db
class Test09GenreTitlesImport:
    """_import_genre_titles: битая строка не останавливает импорт."""

    def test_bad_rows_skipped_good_row_imported(self, tmp_path):
        category = Category.objects.create(name='Книги', slug='books')
        title = Title.objects.create(
            name='Тест', year=2020, category=category
        )
        genre = Genre.objects.create(name='Фантастика', slug='sci-fi')
        csv_path = tmp_path / 'genre_title.csv'
        csv_path.write_text(
            'title_id,genre_id\n'
            f'{title.id},{genre.id}\n'    # валидная строка
            'abc,def\n'                   # не приводится к int
            f'{title.id}\n',              # нет колонки genre_id
            encoding='utf-8',
        )
        command = LoadCsvCommand()
        command.stdout = io.StringIO()

        command._import_genre_titles(csv_path)

        assert title.genre.filter(pk=genre.pk).exists(), (
            'Валидная связь должна быть импортирована.'
        )
        assert command.stdout.getvalue().count('пропущена') == 2, (
            'Битые строки должны пропускаться с предупреждением, '
            'не прерывая импорт остальных связей.'
        )
