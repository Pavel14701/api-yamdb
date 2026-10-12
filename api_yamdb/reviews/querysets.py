"""QuerySet'ы приложения reviews.

Обобщённые фрагменты запросов к БД (аннотации, фильтры, сортировки)
живут здесь, а не в models.py: они про запросы, а не про структуру
данных. Models.py импортирует их для регистрации в качестве менеджера.
"""

from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Avg, IntegerField
from django.db.models.functions import Round
from django.db.models.query import QuerySet

if TYPE_CHECKING:
    # Только для статических проверок: в рантайме Title здесь не нужен,
    # а импорт был бы циклическим (models.py импортирует этот модуль).
    from reviews.models import Title


class TitleQuerySet(models.QuerySet['Title']):
    """QuerySet произведений с аннотациями для выдачи API."""

    def with_rating(self) -> QuerySet['Title']:
        """Аннотирует целочисленный средний рейтинг по отзывам.

        rating — округлённый средний балл; None, если отзывов нет.

        После .annotate() с агрегацией Django (с 2.2) перестаёт
        применять Meta.ordering — иначе оно попадает в GROUP BY и
        ломает запрос. Поэтому нужную сортировку задаём явно через
        .order_by('name').
        """
        return (
            self
            .annotate(
                rating=Round(
                    Avg('reviews__score'),
                    output_field=IntegerField(),
                ),
            )
            .order_by('name')
        )
