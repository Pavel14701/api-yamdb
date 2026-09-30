"""Модели приложения reviews."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from users.models import User


class BaseNameSlugModel(models.Model):
    """Абстрактная базовая модель с полями name и slug."""

    name = models.CharField(
        max_length=256,
        verbose_name='Название',
    )
    slug = models.SlugField(
        max_length=50,
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
        max_length=256,
        verbose_name='Название произведения',
    )
    year = models.IntegerField(
        verbose_name='Год выпуска',
    )
    description = models.TextField(
        blank=True,
        null=True,
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
