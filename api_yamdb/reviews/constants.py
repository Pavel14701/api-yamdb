"""Константы приложения reviews."""

NAME_MAX_LENGTH = 256
SLUG_MAX_LENGTH = 50

SCORE_MIN = 1
SCORE_MAX = 10

# Нижняя граница года произведения: совпадает с минимумом
# SmallIntegerField (поле Title.year) — валидатор отсекает значения,
# которые БД не сможет представить (замечание ревью).
MIN_YEAR = -32768
