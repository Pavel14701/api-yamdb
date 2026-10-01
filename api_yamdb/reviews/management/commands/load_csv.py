"""Management-команда для импорта данных из CSV."""

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from reviews.models import Category, Comment, Genre, Review, Title
from users.models import User


class Command(BaseCommand):
    """Импортирует все CSV файлы в базу данных."""

    help = 'Импортирует данные из CSV файлов в базу данных'

    def handle(self, *args, **options):
        """Основная логика выполнения команды."""
        data_dir = Path(settings.BASE_DIR) / 'static' / 'data'

        self._import_csv(
            data_dir / 'category.csv',
            Category,
            ['id', 'name', 'slug']
        )
        self._import_csv(
            data_dir / 'genre.csv',
            Genre,
            ['id', 'name', 'slug']
        )
        self._import_csv(
            data_dir / 'users.csv',
            User,
            [
                'id', 'username', 'email', 'role', 'bio',
                'first_name', 'last_name'
            ]
        )
        self._import_csv(
            data_dir / 'titles.csv',
            Title,
            ['id', 'name', 'year', 'category_id']
        )
        self._import_csv(
            data_dir / 'review.csv',
            Review,
            ['id', 'title_id', 'text', 'author_id', 'score', 'pub_date']
        )
        self._import_csv(
            data_dir / 'comments.csv',
            Comment,
            ['id', 'review_id', 'text', 'author_id', 'pub_date']
        )
        self._import_genre_titles(data_dir / 'genre_title.csv')

        self.stdout.write(self.style.SUCCESS(
            'Все данные успешно импортированы'
        ))

    def _import_csv(self, file_path, model, fields):
        """Импортирует данные из CSV в указанную модель."""
        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f'Файл не найден: {file_path}'))
            return

        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    defaults = {}
                    for field in fields:
                        if field == 'id':
                            continue
                        csv_field = field
                        if field in ('category_id', 'author_id'):
                            csv_field = field.replace('_id', '')

                        value = row[csv_field]
                        if field in (
                            'year', 'score', 'category_id',
                            'title_id', 'author_id', 'review_id'
                        ):
                            value = int(value)
                        defaults[field] = value

                    model.objects.update_or_create(
                        id=row['id'],
                        defaults=defaults
                    )
                    count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Ошибка в строке {row.get("id", "?")}: {e}'
                        )
                    )

        self.stdout.write(
            f'Импортировано {count} записей модели {model.__name__}'
        )

    def _import_genre_titles(self, file_path):
        """Импортирует связи жанр-произведение (M2M)."""
        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f'Файл не найден: {file_path}'))
            return

        count = 0
        genre_title_relation = Title.genre.through
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    genre_title_relation.objects.get_or_create(
                        title_id=row['title_id'],
                        genre_id=row['genre_id']
                    )
                    count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Ошибка в M2M строке: {e}')
                    )

        self.stdout.write(f'Связано {count} жанров с произведениями')
