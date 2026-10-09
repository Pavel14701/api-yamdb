"""Management-команда для импорта данных из CSV."""

import csv
from pathlib import Path
from typing import Any, Protocol

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from reviews.management.exceptions import CsvImportError, RowSaveError
from reviews.management.parsing import parse_row
from reviews.models import Category, Comment, Genre, Review, Title

# Модель пользователя — как значение таблицы импорта, через
# get_user_model() (замечание ревью), а не прямым импортом.
# Как тип она здесь не используется: типизация таблицы идёт
# через протокол _ModelWithObjects, поэтому танцы с TYPE_CHECKING
# не нужны — результат вызова подойдёт и статическому чекеру.
User = get_user_model()


class _ModelWithObjects(Protocol):
    """Протокол модели с менеджером objects (PEP 544).

    Интерфейс объявляет вызываемая сторона: команда использует только
    наличие менеджера objects (update_or_create, filter), конкретный
    класс модели ей не нужен (замечание ревью про неявные интерфейсы).
    """

    # Any: у моделей разные подтипы менеджеров (UserManager и др.),
    # для команды достаточно самого наличия менеджера и его методов.
    objects: Any


# Таблица импорта: (имя файла, модель, кортеж полей). Порядок важен:
# сначала справочники (category, genre), затем users, titles и
# зависимые (review -> comments). Новая сущность добавляется одной
# строкой сюда, без нового блока кода в handle().
# Pylance джанговсие кульбиты с
# monkey-patching objects в рантайме не вывозит
IMPORT_SPECS: tuple[
    tuple[str, type[_ModelWithObjects], tuple[str, ...]],
    ...,
] = (
    ('category.csv', Category, ('id', 'name', 'slug')),
    ('genre.csv', Genre, ('id', 'name', 'slug')),
    (
        'users.csv',
        User,
        (
            'id', 'username', 'email', 'role', 'bio',
            'first_name', 'last_name',
        ),
    ),
    ('titles.csv', Title, ('id', 'name', 'year', 'category_id')),
    (
        'review.csv',
        Review,
        ('id', 'title_id', 'text', 'author_id', 'score', 'pub_date'),
    ),
    (
        'comments.csv',
        Comment,
        ('id', 'review_id', 'text', 'author_id', 'pub_date'),
    ),
)


class Command(BaseCommand):
    """Импортирует все CSV файлы в базу данных."""

    help = 'Импортирует данные из CSV файлов в базу данных'

    def handle(self, *args: Any, **options: Any) -> None:
        """Основная логика выполнения команды."""
        data_dir = Path(settings.BASE_DIR) / 'static' / 'data'
        for file_name, model, fields in IMPORT_SPECS:
            self._import_csv(data_dir / file_name, model, fields)
        self._import_genre_titles(data_dir / 'genre_title.csv')
        self.stdout.write(self.style.SUCCESS(
            'Все данные успешно импортированы'
        ))

    def _save_row(
        self,
        model: type[_ModelWithObjects],
        row: dict[str, Any],
        defaults: dict[str, Any],
    ) -> None:
        """Сохраняет строку в БД.

        Ошибку БД оборачивает в RowSaveError (boundary-обёртка:
        исходное исключение доступно как __cause__).
        """
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
        except Exception as error:
            raise RowSaveError(row_id, error) from error

    def _import_csv(
        self,
        file_path: Path,
        model: type[_ModelWithObjects],
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
                try:
                    defaults = parse_row(row, fields)
                    self._save_row(model, row, defaults)
                except CsvImportError as import_error:
                    # Ожидаемые ошибки импорта: строка пропускается.
                    self.stdout.write(
                        self.style.WARNING(str(import_error))
                    )
                    continue
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
                row_id = row.get('title_id', '?')
                try:
                    genre_title_relation.objects.get_or_create(
                        title_id=row['title_id'],
                        genre_id=row['genre_id'],
                    )
                except Exception as error:
                    # Битая строка (нет колонки, битый FK, дубль) не
                    # останавливает импорт остальных связей: предупреждение
                    # и переход к следующей строке, как в _import_csv
                    # (замечание ревью).
                    self.stdout.write(
                        self.style.WARNING(
                            f'Строка {row_id} пропущена: {error}'
                        )
                    )
                    continue
                count += 1
        self.stdout.write(f'Связано {count} жанров с произведениями')
