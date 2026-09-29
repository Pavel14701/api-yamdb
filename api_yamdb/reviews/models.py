"""Модели приложения reviews."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from api.models import Title
from users.models import User


class Review(models.Model):
    """Модель отзыва на произведение."""

    title = models.ForeignKey(
        Title,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Произведение',
    )
    text = models.TextField(verbose_name='Текст отзыва')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Автор отзыва',
    )
    score = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, 'Оценка не может быть ниже 1'),
            MaxValueValidator(10, 'Оценка не может быть выше 10')
        ],
        verbose_name='Оценка произведения',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата публикации отзыва',
    )

    class Meta:
        """Настройки отображения модели."""

        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ('-pub_date',)
        constraints = [
            models.UniqueConstraint(
                fields=['title', 'author'],
                name='unique_title_author_review'
            )
        ]

    def __str__(self) -> str:
        """Возвращает краткое описание отзыва."""
        return f'Отзыв от {self.author} на {self.title}'


class Comment(models.Model):
    """Модель комментария к отзыву."""

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Отзыв',
    )
    text = models.TextField(verbose_name='Текст комментария')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор комментария',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата публикации комментария',
    )

    class Meta:
        """Настройки отображения модели."""

        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        """Возвращает краткое описание комментария."""
        return f'Комментарий от {self.author} к отзыву {self.review.id}'
