"""Модели приложения reviews."""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from reviews.constants import (
    NAME_MAX_LENGTH,
    SCORE_MAX,
    SCORE_MIN,
    SLUG_MAX_LENGTH,
)
from users.models import User


def current_year():
    """Возвращает текущий год."""
    return datetime.now().year


def validate_year(value):
    """Валидатор: год не должен быть больше текущего."""
    if value > current_year():
        raise ValidationError(
            f'Год выпуска не может быть больше текущего ({current_year()}).',
            code='invalid_year',
        )


class BaseNameSlugModel(models.Model):
    """Абстрактная базовая модель с полями name и slug."""
    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Название',
    )
    slug = models.SlugField(
        max_length=SLUG_MAX_LENGTH,
        unique=True,
        verbose_name='Slug',
    )

    class Meta:
        """Настройки метаданных для всех наследуемых моделей."""
        abstract = True
        ordering = ('name',)

    def __str__(self) -> str:
        """Возвращает название объекта."""
        return self.name


class Category(BaseNameSlugModel):
    """Модель категории произведений."""
    class Meta(BaseNameSlugModel.Meta):
        """Настройки метаданных модели Category."""
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Genre(BaseNameSlugModel):
    """Модель жанра произведения."""
    class Meta(BaseNameSlugModel.Meta):
        """Настройки метаданных модели Genre."""
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'


class Title(models.Model):
    """Модель произведения (фильм, книга, песня и т.д.)."""
    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Название произведения',
    )
    year = models.IntegerField(
        validators=[validate_year],
        db_index=True,
        verbose_name='Год выпуска',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='titles',
        verbose_name='Категория',
    )
    genre = models.ManyToManyField(
        Genre,
        related_name='titles',
        verbose_name='Жанры',
    )

    class Meta:
        """Настройки метаданных модели Title."""
        verbose_name = 'Произведение'
        verbose_name_plural = 'Произведения'
        ordering = ('name',)

    def __str__(self) -> str:
        """Возвращает название произведения."""
        return self.name


class Review(models.Model):
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
            MinValueValidator(SCORE_MIN, 'Оценка не может быть ниже 1'),
            MaxValueValidator(SCORE_MAX, 'Оценка не может быть выше 10')
        ],
        verbose_name='Оценка произведения',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата публикации отзыва',
    )

    class Meta:
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
        return f'Отзыв от {self.author} на {self.title}'


class Comment(models.Model):
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
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return f'Комментарий от {self.author} к отзыву {self.review.id}'
