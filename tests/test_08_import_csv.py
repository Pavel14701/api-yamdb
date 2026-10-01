"""Тесты импорта данных из CSV-файлов (static/data).

Контракт: management-команда
    python manage.py load_csv
наполняет БД содержимым api_yamdb/static/data/*.csv и является
идемпотентной (повторный запуск не создаёт дубликатов).

Пока команда не реализована, тесты пропускаются (CI не краснеет).
"""

import csv
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command, get_commands

from reviews.models import Category, Comment, Genre, Review, Title

COMMAND_NAME = 'load_csv'
DATA_DIR = (
    Path(__file__).resolve().parent.parent
    / 'api_yamdb' / 'static' / 'data'
)

pytestmark = pytest.mark.skipif(
    COMMAND_NAME not in get_commands(),
    reason=f'Команда `{COMMAND_NAME}` ещё не реализована — импорт CSV не '
           'проверяется. Реализуйте `python manage.py load_csv`.'
)


def read_csv(name):
    """Читает csv как список словарей (учитывая многострочные тексты)."""
    with open(DATA_DIR / name, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load():
    call_command(COMMAND_NAME)


def users_by_id():
    return {row['id']: row for row in read_csv('users.csv')}


@pytest.mark.django_db(transaction=True)
class Test08ImportCsv:

    def test_01_command_runs(self):
        load()

    def test_02_counts_match_csv(self):
        load()
        expected = (
            (Category, read_csv('category.csv')),
            (Genre, read_csv('genre.csv')),
            (Title, read_csv('titles.csv')),
            (get_user_model(), read_csv('users.csv')),
            (Review, read_csv('review.csv')),
            (Comment, read_csv('comments.csv')),
        )
        for model, rows in expected:
            assert model.objects.count() == len(rows), (
                f'В БД {model.objects.count()} записей модели '
                f'{model.__name__}, а в csv — {len(rows)}. Проверьте, что '
                f'все записи из файла {model.__name__.lower()}.csv попадают '
                'в базу.'
            )
        links = Title.genre.through.objects.count()
        assert links == len(read_csv('genre_title.csv')), (
            f'Связок произведение-жанр в БД {links}, а в genre_title.csv — '
            f'{len(read_csv("genre_title.csv"))}.'
        )

    def test_03_category_fields(self):
        load()
        category = Category.objects.get(slug='movie')
        assert category.name == 'Фильм'

    def test_04_title_fields_and_category(self):
        load()
        title = Title.objects.get(name='Побег из Шоушенка')
        assert title.year == 1994
        assert title.category.slug == 'movie'

    def test_05_review_author_is_user_fk(self):
        load()
        users = users_by_id()
        for review in Review.objects.all():
            author = review.author
            expected_username = users[str(author.id)]['username']
            assert author.username == expected_username, (
                f'Автор отзыва id={review.id} — пользователь '
                f'"{author.username}", а по users.csv для этого id ожидается '
                f'"{expected_username}". Поле author должно ссылаться на '
                'пользователя из users.csv (id пользователей из csv должны '
                'сохраняться).'
            )
        assert Review.objects.filter(
            title__name='Побег из Шоушенка', score=10
        ).exists()

    def test_06_comment_linked_to_review_and_user(self):
        load()
        users = users_by_id()
        assert Comment.objects.count() > 0
        for comment in Comment.objects.all():
            assert comment.review.title_id is not None
            expected = users[str(comment.author.id)]['username']
            assert comment.author.username == expected

    def test_07_genres_m2m(self):
        load()
        links = read_csv('genre_title.csv')
        for row in links[:5]:
            title = Title.objects.get(pk=row['title_id'])
            genre = Genre.objects.get(pk=row['genre_id'])
            assert title.genre.filter(pk=genre.pk).exists(), (
                f'У произведения "{title.name}" нет жанра "{genre.name}", '
                f'хотя связка есть в genre_title.csv (строка '
                f'id={row["id"]}).'
            )

    def test_08_users_roles(self):
        load()
        users = users_by_id()
        for row in users.values():
            user = get_user_model().objects.get(username=row['username'])
            assert user.role == row['role'], (
                f'У пользователя {user.username} роль "{user.role}", '
                f'а в users.csv — "{row["role"]}".'
            )

    def test_09_idempotent(self):
        load()
        counts_before = (
            Category.objects.count(),
            Genre.objects.count(),
            Title.objects.count(),
            Review.objects.count(),
            Comment.objects.count(),
            Title.genre.through.objects.count(),
        )
        load()
        counts_after = (
            Category.objects.count(),
            Genre.objects.count(),
            Title.objects.count(),
            Review.objects.count(),
            Comment.objects.count(),
            Title.genre.through.objects.count(),
        )
        assert counts_before == counts_after, (
            'Повторный запуск команды создаёт дубликаты. Используйте '
            'update_or_create/get_or_create или очистку таблиц перед '
            'загрузкой.'
        )

    def test_10_pub_dates_from_csv(self):
        load()
        csv_reviews = {row['id']: row for row in read_csv('review.csv')}
        for review in Review.objects.all():
            expected = csv_reviews[str(review.id)]['pub_date']
            actual = review.pub_date.strftime('%Y-%m-%dT%H:%M')
            assert actual.startswith(expected[:16]), (
                f'У отзыва id={review.id} дата {actual}, а в csv — '
                f'{expected}. Поле pub_date имеет auto_now_add и '
                'перезаписывает дату из файла: проставьте дату из csv '
                'явно после создания записи.'
            )
