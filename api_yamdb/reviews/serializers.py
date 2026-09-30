"""Сериализаторы для отзывов и комментариев."""

from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from reviews.models import Comment, Review
from users.models import User


class ReviewSerializer(serializers.ModelSerializer[Review]):
    """Сериализатор для работы с моделью отзывов (Review)."""

    author = serializers.SlugRelatedField[User](
        slug_field='username',
        read_only=True,
    )

    class Meta:
        """Настройки сериализатора Review."""

        model = Review
        fields = ('id', 'text', 'author', 'score', 'pub_date')
        read_only_fields = ('author', 'pub_date')

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Проверка уникальности отзыва."""
        request = self.context.get('request')
        view = self.context.get('view')
        if request and view and request.method == 'POST':
            author = request.user
            title_id = view.kwargs.get('title_id')
            if Review.objects.filter(
                author=author, title_id=title_id
            ).exists():
                raise ValidationError(
                    'Вы уже оставили отзыв на это произведение!'
                )
        return data


class CommentSerializer(serializers.ModelSerializer[Comment]):
    """Сериализатор для работы с моделью комментариев (Comment)."""

    author = serializers.SlugRelatedField[User](
        slug_field='username',
        read_only=True,
    )

    class Meta:
        """Настройки сериализатора Comment."""

        model = Comment
        fields = ('id', 'text', 'author', 'pub_date')
        read_only_fields = ('author', 'pub_date')
