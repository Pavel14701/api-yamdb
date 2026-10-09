"""Кастомные исключения management-команд импорта CSV."""


class CsvImportError(Exception):
    """Базовая ошибка импорта CSV.

    Ожидаемое исключение: команда ловит его, пишет предупреждение
    и переходит к следующей строке. Любые другие исключения
    (опечатки, битая конфигурация) не глушатся и падают громко.
    """


class MissingColumnError(CsvImportError):
    """В строке CSV отсутствует ожидаемая колонка."""

    def __init__(self, row_id: str, column: str) -> None:
        """Сохраняет номер строки и имя колонки для сообщения."""
        self.row_id = row_id
        self.column = column
        super().__init__(f'В строке {row_id} нет колонки {column}')


class FieldParseError(CsvImportError):
    """Значение колонки не приводится к нужному типу."""

    def __init__(self, row_id: str, message: str) -> None:
        """Сохраняет номер строки и текст ошибки парсинга."""
        self.row_id = row_id
        super().__init__(f'Ошибка парсинга в строке {row_id}: {message}')


class RowSaveError(CsvImportError):
    """Ошибка сохранения строки в БД.

    Исходное исключение БД доступно через __cause__ (raise ... from).
    """
