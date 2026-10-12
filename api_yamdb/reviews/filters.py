"""Фильтры для API."""

import django_filters  # type: ignore[import-untyped]

from reviews.models import Title


class TitleFilter(django_filters.FilterSet):  # type: ignore[misc]
    """Фильтрация произведений по категории, жанру, названию и году."""

    category = django_filters.CharFilter(field_name='category__slug')
    genre = django_filters.CharFilter(field_name='genre__slug')
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains'
    )

    class Meta:
        """Настройки фильтра Title."""

        model = Title
        fields = ('category', 'genre', 'name', 'year')
