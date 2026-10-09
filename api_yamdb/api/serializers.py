"""Сериализаторы контента: произведения, категории, жанры, отзывы.

Сериализаторы домена пользователей (регистрация, токен, /users/)
живут в users/serializers.py.
"""

from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from reviews.models import Category, Comment, Genre, Review, Title

if TYPE_CHECKING:
    # В аннотациях типов нужен настоящий класс, а не результат вызова.
    # Аннотации разбирает статический чекер ДО запуска программы:
    # он не исполняет функции и не знает, что вернёт get_user_model(),
    # поэтому видит в User обычную переменную, а переменную нельзя
    # использовать как тип (mypy: «Variable ... is not valid as a
    # type»). Класс из users.models чекер знает и проверяет
    # дженерики вида ModelSerializer['User'].
    from users.models import User
else:
    # В рантайме модель не импортируем напрямую (замечание ревью):
    # получаем через get_user_model(), чтобы код зависел от настройки
    # AUTH_USER_MODEL из settings, а не от конкретного класса.
    User = get_user_model()


def _author_username_field() -> serializers.SlugRelatedField['User']:
    """Фабрика общего поля author: username, только чтение.

    Review и Comment показывают автора одинаково. Каждый вызов
    возвращает новый экземпляр поля — общие экземпляры полей
    между классами не создаются.
    """
    return serializers.SlugRelatedField['User'](
        slug_field='username',
        read_only=True,
    )


class ReviewSerializer(serializers.ModelSerializer['Review']):
    """Сериализатор для работы с моделью отзывов (Review)."""

    author = _author_username_field()

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
            # Прямой запрос к Review вместо join через Title —
            # то же условие: отзыв этого автора на это произведение.
            if Review.objects.filter(
                title_id=title_id,
                author=author,
            ).exists():
                raise ValidationError(
                    'Вы уже оставили отзыв на это произведение!'
                )
        return data


class CommentSerializer(serializers.ModelSerializer['Comment']):
    """Сериализатор для работы с моделью комментариев (Comment)."""

    author = _author_username_field()

    class Meta:
        """Настройки сериализатора Comment."""

        model = Comment
        fields = ('id', 'text', 'author', 'pub_date')
        read_only_fields = ('author', 'pub_date')


class CategorySerializer(serializers.ModelSerializer['Category']):
    """Сериализатор для работы с моделью категорий (Category)."""

    class Meta:
        """Настройки сериализатора Category."""

        model = Category
        fields = ('name', 'slug')


class GenreSerializer(serializers.ModelSerializer['Genre']):
    """Сериализатор для работы с моделью жанров (Genre)."""

    class Meta:
        """Настройки сериализатора Genre."""

        model = Genre
        fields = ('name', 'slug')


class TitleReadSerializer(serializers.ModelSerializer['Title']):
    """Сериализатор для чтения произведений (GET-запросы)."""

    genre = GenreSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    rating = serializers.IntegerField(read_only=True)

    class Meta:
        """Настройки сериализатора чтения Title."""

        model = Title
        fields = (
            'id',
            'name',
            'year',
            'rating',
            'description',
            'genre',
            'category',
        )


class TitleWriteSerializer(serializers.ModelSerializer['Title']):
    """Сериализатор для создания/обновления произведений (POST, PATCH)."""

    genre = serializers.SlugRelatedField['Genre'](
        many=True,
        slug_field='slug',
        allow_empty=False,
        queryset=Genre.objects.all(),
    )
    category = serializers.SlugRelatedField['Category'](
        slug_field='slug',
        queryset=Category.objects.all(),
    )

    class Meta:
        """Настройки сериализатора записи Title."""

        model = Title
        fields = ('id', 'name', 'year', 'description', 'genre', 'category')
