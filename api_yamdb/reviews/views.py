"""ViewSet для отзывов и комментариев."""

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from api.permissions import IsAuthorModeratorAdminOrReadOnly
from reviews.models import Review, Title
from reviews.serializers import CommentSerializer, ReviewSerializer


class ReviewPagination(PageNumberPagination):
    """Пагинация для отзывов."""

    page_size = 10


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с отзывами."""

    permission_classes = (IsAuthorModeratorAdminOrReadOnly,)
    pagination_class = ReviewPagination
    serializer_class = ReviewSerializer

    def get_queryset(self):
        """Возвращает QuerySet отзывов для конкретного произведения."""
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        return title.reviews.all()

    def perform_create(self, serializer):
        """Сохраняет отзыв с привязкой к произведению и автору."""
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с комментариями."""

    permission_classes = (IsAuthorModeratorAdminOrReadOnly,)
    pagination_class = ReviewPagination
    serializer_class = CommentSerializer

    def get_queryset(self):
        """Возвращает QuerySet комментариев к конкретному отзыву."""
        review = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title_id=self.kwargs.get('title_id')
        )
        return review.comments.all()

    def perform_create(self, serializer):
        """Сохраняет комментарий с привязкой к отзыву и автору."""
        review = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title_id=self.kwargs.get('title_id')
        )
        serializer.save(author=self.request.user, review=review)
