"""Management-команда для импорта данных из CSV."""

import csv
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from reviews.models import Category, Comment, Genre, Review, Title
from users.models import User


class Command(BaseCommand):
    """Импортирует все CSV файлы в базу данных."""

    help = 'Импортирует данные из CSV файлов в базу данных'

    def handle(self, *args: Any, **options: Any) -> None:
        """Основная логика выполнения команды."""
        data_dir = Path(settings.BASE_DIR) / 'static' / 'data'

        self._import_csv(
            data_dir / 'category.csv',
            Category,
            ('id', 'name', 'slug')
        )
        self._import_csv(
            data_dir / 'genre.csv',
            Genre,
            ('id', 'name', 'slug')
        )
        self._import_csv(
            data_dir / 'users.csv',
            User,
            (
                'id', 'username', 'email', 'role', 'bio',
                'first_name', 'last_name'
            )
        )
        self._import_csv(
            data_dir / 'titles.csv',
            Title,
            ('id', 'name', 'year', 'category_id')
        )
        self._import_csv(
            data_dir / 'review.csv',
            Review,
            ('id', 'title_id', 'text', 'author_id', 'score', 'pub_date')
        )
        self._import_csv(
            data_dir / 'comments.csv',
            Comment,
            ('id', 'review_id', 'text', 'author_id', 'pub_date')
        )
        self._import_genre_titles(data_dir / 'genre_title.csv')

        self.stdout.write(self.style.SUCCESS(
            'Все данные успешно импортированы'
        ))

    def _parse_row(
            self,
            row: dict[str, Any],
            fields: tuple[str, ...],
    ) -> dict[str, Any] | None:
        """Парсит строку CSV и возвращает словарь."""
        row_id = row.get('id', '?')
        try:
            defaults = {}
            for field in fields:
                if field == 'id':
                    continue
                csv_field = field
                if field in {'category_id', 'author_id'}:
                    csv_field = field.replace('_id', '')

                field_value = row[csv_field]
                if field in {
                    'year', 'score', 'category_id',
                    'title_id', 'author_id', 'review_id'
                }:
                    field_value = int(field_value)
                defaults[field] = field_value
            return defaults
        except (KeyError, ValueError) as parse_error:
            self.stdout.write(
                self.style.WARNING(
                    f'Ошибка парсинга в строке {row_id}: {parse_error}'
                )
            )
            return None

    def _save_row(
        self,
        model: type[Any],
        row: dict[str, Any],
        defaults: dict[str, Any],
    ) -> bool:
        """Сохраняет строку в БД. Возвращает True при успехе, иначе False."""
        row_id = row.get('id', '?')
        try:
            obj, _ = model.objects.update_or_create(
                id=row['id'],
                defaults=defaults
            )
            if 'pub_date' in defaults:
                model.objects.filter(pk=obj.pk).update(
                    pub_date=defaults['pub_date']
                )
            return True
        except Exception as error:
            self.stdout.write(
                self.style.WARNING(
                    f'Ошибка в строке {row_id}: {error}'
                )
            )
        return False

    def _import_csv(
        self,
        file_path: Path,
        model: type[Any],
        fields: tuple[str, ...],
    ) -> None:
        """Импортирует данные из CSV в указанную модель."""
        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f'Файл не найден: {file_path}'))
            return

        count = 0
        with open(file_path, encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                defaults = self._parse_row(row, fields)
                if defaults is None:
                    continue
                if self._save_row(model, row, defaults):
                    count += 1

        self.stdout.write(
            f'Импортировано {count} записей модели {model.__name__}'
        )

    def _import_genre_titles(self, file_path: Path) -> None:
        """Импортирует связи жанр-произведение (M2M)."""
        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f'Файл не найден: {file_path}'))
            return

        count = 0
        genre_title_relation = Title.genre.through
        with open(file_path, encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                try:
                    genre_title_relation.objects.get_or_create(
                        title_id=row['title_id'],
                        genre_id=row['genre_id']
                    )
                    count += 1

                except Exception as error:
                    self.stdout.write(
                        self.style.WARNING(f'Ошибка в M2M строке: {error}')
                    )

        self.stdout.write(f'Связано {count} жанров с произведениями')
