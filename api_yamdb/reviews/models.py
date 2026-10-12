"""Модели приложения reviews."""

from datetime import datetime
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from reviews.constants import (
    MIN_YEAR,
    NAME_MAX_LENGTH,
    SCORE_MAX,
    SCORE_MIN,
    SLUG_MAX_LENGTH,
)

# Импорт QuerySet'а из отдельного модуля: models.py отвечает за
# структуру данных, а логика запросов живёт в querysets.py.
from reviews.querysets import TitleQuerySet

# Прямой импорт класса пользователя для FK: users — проектное
# приложение, цикла нет; для локальной модели это эквивалент
# settings.AUTH_USER_MODEL, но сохраняет статическую типизацию FK.
# проще джангу переписать чем эти стабы заставить работать
if TYPE_CHECKING:
    from users.models import User
else:
    User = get_user_model()


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


class Title(models.Model):
    """Модель произведения (фильм, книга, песня и т.д.)."""

    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Название произведения',
    )
    year = models.SmallIntegerField(
        # SmallIntegerField: 2 байта, диапазон -32768..32767 — хватает
        # и на произведения Древнего Рима (отрицательные годы), и на
        # ~30000 лет вперёд.
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

    # Менеджер — после полей, до Meta (порядок из coding-style Django).
    objects = TitleQuerySet.as_manager()

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
            MaxValueValidator(SCORE_MAX, 'Оценка не может быть выше 10'),
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
