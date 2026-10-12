"""ViewSet для отзывов, комментариев, категорий, жанров и произведений."""

from typing import Any, cast

from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import (  # type: ignore[import-untyped]
    DjangoFilterBackend,
)
from rest_framework import filters, mixins, viewsets
from rest_framework.serializers import BaseSerializer

from api.permissions import (
    IsAdminOrReadOnly,
    IsAuthorModeratorAdminOrReadOnly,
)
from reviews.api.v1.serializers import (
    CategorySerializer,
    CommentSerializer,
    GenreSerializer,
    ReviewSerializer,
    TitleReadSerializer,
    TitleWriteSerializer,
)
from reviews.filters import TitleFilter
from reviews.models import Category, Comment, Genre, Review, Title


class CategoryViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet[Category],
):
    """ViewSet для категорий: список, создание, удаление по slug."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'


class GenreViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet[Genre],
):
    """ViewSet для жанров: список, создание, удаление по slug."""

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'


class TitleViewSet(viewsets.ModelViewSet[Title]):
    """ViewSet для произведений: полный CRUD с фильтрацией."""

    queryset = Title.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = TitleFilter
    ordering_fields = ('name', 'year', 'rating')
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def get_queryset(self) -> QuerySet[Title]:
        """Возвращает список произведений с целым округлённым рейтингом."""
        # Формула рейтинга — доменное знание, живёт в модели
        # (TitleQuerySet.with_rating), вьюха только запрашивает.
        return Title.objects.with_rating()

    def get_serializer_class(
        self,
    ) -> type[TitleReadSerializer | TitleWriteSerializer]:
        """Возвращает сериализатор чтения или записи по экшену."""
        if self.action in {'create', 'update', 'partial_update'}:
            return TitleWriteSerializer
        return TitleReadSerializer


class ReviewViewSet(viewsets.ModelViewSet[Review]):
    """ViewSet для работы с отзывами."""

    permission_classes = (IsAuthorModeratorAdminOrReadOnly,)
    serializer_class = ReviewSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('pub_date', 'score')
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def _get_title(self) -> Title:
        """Возвращает произведение по title_id из kwargs (404, если нет).

        Результат кэшируется на время запроса: get_queryset и
        perform_create запрашивают одно и то же произведение, и без
        кэша это два одинаковых SELECT'а на один POST.
        kwargs.get('title_id') теоретически может дать None —
        get_object_or_404(Title, id=None) не найдёт совпадения
        и вернёт те же 404, отдельная проверка избыточна.
        """
        if not hasattr(self, '_title_cache'):
            self._title_cache = get_object_or_404(
                Title, id=self.kwargs.get('title_id')
            )
        return self._title_cache

    def get_queryset(self) -> QuerySet[Review]:
        """Возвращает QuerySet отзывов для конкретного произведения."""
        return self._get_title().reviews.all()

    def get_serializer_context(self) -> dict[str, Any]:
        """Добавляет title_id в контекст сериализатора.

        ReviewSerializer.validate берёт title_id отсюда, чтобы
        проверить уникальность пары (title, author) до INSERT'а
        и вернуть 400 вместо IntegrityError → 500.
        """
        # Тут прикольная ситуация и не понятно кому верить,
        # super().get_serializer_context() возвращает Маппинг,
        # т.е. контракт на чтение, а сам этот метод даже в туториалах
        # используется в основном только для мутации контекста.
        # Отдельный сюр в том, что создали стабов и создатели либы,
        # считай одни и те же люди.
        context: dict[str, Any] = cast(
            dict[str, Any],
            super().get_serializer_context()
        )
        context['title_id'] = self.kwargs.get('title_id')
        return context

    def perform_create(self, serializer: BaseSerializer[Review]) -> None:
        """Сохраняет отзыв с привязкой к произведению и автору."""
        serializer.save(
            author=self.request.user,
            title=self._get_title(),
        )


class CommentViewSet(viewsets.ModelViewSet[Comment]):
    """ViewSet для работы с комментариями."""

    permission_classes = (IsAuthorModeratorAdminOrReadOnly,)
    serializer_class = CommentSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('pub_date',)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def _get_review(self) -> Review:
        """Возвращает отзыв по review_id и title_id (404, если нет).

        Результат кэшируется на время запроса: get_queryset и
        perform_create запрашивают один и тот же отзыв, без кэша
        это два одинаковых SELECT'а на один POST.
        """
        if not hasattr(self, '_review_cache'):
            self._review_cache = get_object_or_404(
                Review,
                id=self.kwargs.get('review_id'),
                title_id=self.kwargs.get('title_id'),
            )
        return self._review_cache

    def get_queryset(self) -> QuerySet[Comment]:
        """Возвращает QuerySet комментариев к конкретному отзыву."""
        return self._get_review().comments.all()

    def perform_create(self, serializer: BaseSerializer[Comment]) -> None:
        """Сохраняет комментарий с привязкой к отзыву и автору."""
        serializer.save(
            author=self.request.user,
            review=self._get_review(),
        )