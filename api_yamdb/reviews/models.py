"""Модели приложения reviews."""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, IntegerField
from django.db.models.functions import Round
from django.db.models.query import QuerySet

from reviews.constants import (
    MIN_YEAR,
    NAME_MAX_LENGTH,
    SCORE_MAX,
    SCORE_MIN,
    SLUG_MAX_LENGTH,
)

# Прямой импорт класса пользователя для FK: users — проектное
# приложение, цикла нет; для локальной модели это эквивалент
# settings.AUTH_USER_MODEL, но сохраняет статическую типизацию FK.
from users.models import User


def current_year() -> int:
    """Возвращает текущий год."""
    return datetime.now().year


def validate_year(value: int) -> None:
    """Валидатор: год в границах [MIN_YEAR, текущий год].

    Нижняя граница — минимум SmallIntegerField поля year: значение
    отсекается валидатором раньше, чем его отвергнет БД (замечание
    ревью о непредставимых значениях).
    """
    current = current_year()
    if value > current:
        raise ValidationError(
            f'Год выпуска не может быть больше текущего ({current}).',
            code='invalid_year',
        )
    if value < MIN_YEAR:
        raise ValidationError(
            f'Год выпуска не может быть меньше {MIN_YEAR}.',
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


class TitleQuerySet(models.QuerySet['Title']):
    """QuerySet произведений с аннотациями для выдачи API."""

    def with_rating(self) -> QuerySet['Title']:
        """Аннотирует целочисленный средний рейтинг по отзывам.

        rating — округлённый средний балл; None, если отзывов нет.
        Аннотация не сбрасывает Meta.ordering ('name'), сортировка
        остаётся по названию.
        """
        queryset: QuerySet[Title] = self.annotate(
            rating=Round(Avg('reviews__score'), output_field=IntegerField()),
        )
        return queryset


class Title(models.Model):
    """Модель произведения (фильм, книга, песня и т.д.)."""

    objects = TitleQuerySet.as_manager()

    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Название произведения',
    )
    year = models.SmallIntegerField(
        # SmallIntegerField: 2 байта, диапазон -32768..32767 — хватает
        # и на произведения Древнего Рима (отрицательные годы), и на
        # ~30000 лет вперёд (замечание ревью).
        validators=(validate_year,),
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
        """Метаданные модели отзыва: имена и порядок сортировки."""

        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ('-pub_date',)
        constraints = (
            models.UniqueConstraint(
                fields=('title', 'author'),
                name='unique_title_author_review',
            ),
        )

    def __str__(self) -> str:
        """Возвращает краткое описание отзыва (автор и произведение)."""
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
        """Метаданные модели комментария: имена и порядок сортировки."""

        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        """Возвращает краткое описание комментария (автор и ID отзыва)."""
        return f'Комментарий от {self.author} к отзыву {self.review.id}'
