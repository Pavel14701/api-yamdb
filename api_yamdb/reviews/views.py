"""ViewSet для отзывов и комментариев."""

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from api.models import Title
from reviews.models import Comment, Review
from reviews.permissions import IsAuthorOrModeratorOrAdminOrReadOnly
from reviews.serializers import CommentSerializer, ReviewSerializer


class ReviewPagination(PageNumberPagination):
    """Пагинация для отзывов."""

    page_size = 10


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с отзывами."""

    permission_classes = (IsAuthorOrModeratorOrAdminOrReadOnly,)
    pagination_class = ReviewPagination

    def get_serializer_class(self):
        """Возвращает сериализатор для Review."""
        return ReviewSerializer

    def get_queryset(self):
        """Возвращает отзывы для конкретного произведения."""
        title_id = self.kwargs.get('title_id')
        return get_object_or_404(Review, title_id=title_id)

    def perform_create(self, serializer):
        """Сохраняет отзыв с привязкой к произведению и автору."""
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, id=title_id)
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с комментариями."""

    permission_classes = (IsAuthorOrModeratorOrAdminOrReadOnly,)

    def get_serializer_class(self):
        """Возвращает сериализатор для Comment."""
        return CommentSerializer

    def get_queryset(self):
        """Возвращает комментарии к конкретному отзыву."""
        review_id = self.kwargs.get('review_id')
        return get_object_or_404(Comment, review_id=review_id)

    def perform_create(self, serializer):
        """Сохраняет комментарий с привязкой к отзыву и автору."""
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(Review, id=review_id)
        serializer.save(author=self.request.user, review=review)
