"""ViewSet для отзывов, комментариев, категорий, жанров и произведений."""

import django_filters
from django.db.models import Avg, IntegerField, QuerySet
from django.db.models.functions import Round
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.serializers import BaseSerializer, ModelSerializer

from api.permissions import IsAdminOrReadOnly, IsAuthorModeratorAdminOrReadOnly
from api.serializers import (
    CategorySerializer,
    CommentSerializer,
    GenreSerializer,
    ReviewSerializer,
    TitleReadSerializer,
    TitleWriteSerializer,
)
from reviews.models import Category, Comment, Genre, Review, Title


class ReviewPagination(PageNumberPagination):
    """Пагинация для отзывов."""

    page_size = 10


class TitleFilter(django_filters.FilterSet):
    """Фильтрация произведений по категории, жанру, названию и году."""

    category = django_filters.CharFilter(field_name='category__slug')
    genre = django_filters.CharFilter(field_name='genre__slug')
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains'
    )
    year = django_filters.NumberFilter(field_name='year')

    class Meta:
        """Настройки фильтра Title."""

        model = Title
        fields = ('category', 'genre', 'name', 'year')


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
    pagination_class = ReviewPagination
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
    pagination_class = ReviewPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'


class TitleViewSet(viewsets.ModelViewSet[Title]):
    """ViewSet для произведений: полный CRUD с фильтрацией."""

    queryset = Title.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = ReviewPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitleFilter
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self) -> QuerySet[Title]:
        """Возвращает список произведений с целым округленным рейтингом."""
        return Title.objects.annotate(
            rating=Round(Avg('reviews__score'), output_field=IntegerField())
        ).order_by('name')

    def get_serializer_class(self) -> type[ModelSerializer[Title]]:
        """Возвращает сериализатор чтения или записи по экшену."""
        if self.action in ('create', 'update', 'partial_update'):
            return TitleWriteSerializer
        return TitleReadSerializer


class ReviewViewSet(viewsets.ModelViewSet[Review]):
    """ViewSet для работы с отзывами."""

    permission_classes = (IsAuthorModeratorAdminOrReadOnly,)
    pagination_class = ReviewPagination
    serializer_class = ReviewSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self) -> QuerySet[Review]:
        """Возвращает QuerySet отзывов для конкретного произведения."""
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        return title.reviews.all()

    def perform_create(self, serializer: BaseSerializer[Review]) -> None:
        """Сохраняет отзыв с привязкой к произведению и автору."""
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet[Comment]):
    """ViewSet для работы с комментариями."""

    permission_classes = (IsAuthorModeratorAdminOrReadOnly,)
    pagination_class = ReviewPagination
    serializer_class = CommentSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self) -> QuerySet[Comment]:
        """Возвращает QuerySet комментариев к конкретному отзыву."""
        review = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title_id=self.kwargs.get('title_id')
        )
        return review.comments.all()

    def perform_create(self, serializer: BaseSerializer[Comment]) -> None:
        """Сохраняет комментарий с привязкой к отзыву и автору."""
        review = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title_id=self.kwargs.get('title_id')
        )
        serializer.save(author=self.request.user, review=review)
