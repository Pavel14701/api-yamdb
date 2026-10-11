"""Кастомные наборы запросов (QuerySets) для моделей отзывов."""

from django.db.models import Avg, IntegerField, QuerySet
from django.db.models.functions import Round
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reviews.models import Title


class TitleQuerySet(QuerySet['Title']):
    """QuerySet произведений с аннотациями для выдачи API."""

    def with_rating(self) -> QuerySet['Title']:
        """Аннотирует целочисленный средний рейтинг по отзывам."""
        return self.annotate(
            rating=Round(Avg('reviews__score'), output_field=IntegerField()),
        ).order_by('name')
