"""Парсинг строк CSV для команды импорта.

Чистая логика без обращения к БД: модуль можно тестировать без
Django. Бросает исключения из reviews.management.exceptions,
которые команда ловит как ожидаемые.
"""

from typing import Any

from reviews.management.exceptions import (
    FieldParseError,
    MissingColumnError,
)

# Поля, значения которых в CSV нужно привести к int.
NUMERIC_FIELDS = frozenset({
    'year', 'score', 'category_id', 'title_id', 'author_id', 'review_id',
})

# Соответствие полей модели и колонок CSV: в CSV колонка называется
# без суффикса _id (author, category), а поле модели — с ним.
CSV_FIELD_ALIASES = {
    'category_id': 'category',
    'author_id': 'author',
}


def parse_row(
        row: dict[str, Any],
        fields: tuple[str, ...],
) -> dict[str, Any]:
    """Парсит строку CSV и возвращает словарь значений полей.

    Бросает MissingColumnError, если в строке нет колонки, и
    FieldParseError, если значение не приводится к числу. Оба
    ловятся в Command._import_csv: строка пропускается с
    предупреждением, импорт продолжается.
    """
    row_id = row.get('id', '?')
    defaults: dict[str, Any] = {}
    for field in fields:
        if field == 'id':
            continue
        csv_field = CSV_FIELD_ALIASES.get(field, field)
        if csv_field not in row:
            raise MissingColumnError(row_id, csv_field)
        field_value = row[csv_field]
        if field in NUMERIC_FIELDS:
            # try/except намеренно узкий — только приведение к int.
            # TypeError тоже ожидаем: csv.DictReader отдаёт None для
            # отсутствующей ячейки, и int(None) — это TypeError,
            # а не ValueError (замечание ревью).
            try:
                field_value = int(field_value)
            except (ValueError, TypeError) as parse_error:
                raise FieldParseError(
                    row_id, str(parse_error),
                ) from parse_error
        defaults[field] = field_value
    return defaults
