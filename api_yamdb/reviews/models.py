"""Модуль моделей API: категории, жанры и произведения."""

from django.db import models


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
