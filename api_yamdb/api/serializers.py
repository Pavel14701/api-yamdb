"""Сериализаторы для регистрации, токенов, пользователей и контента.

Контент: произведения, категории, жанры, отзывы и комментарии.
"""

import hmac
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from api_yamdb.constants import (
    MAX_LENGTH_CONFIRMATION_CODE,
    MAX_LENGTH_EMAIL,
    MAX_LENGTH_USERNAME,
)
from reviews.models import Category, Comment, Genre, Review, Title
from users.codes import hash_confirmation_code
from users.models import validate_username

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

MSG_WRONG_CONFIRMATION_CODE = 'Неверный код подтверждения.'


class SignUpSerializer(serializers.Serializer[dict[str, Any]]):
    """Сериализатор самостоятельной регистрации пользователя.

    Валидация username (формат + запрет имени "me") подхватывается
    из валидатора модели пользователя.
    """

    email = serializers.EmailField(max_length=MAX_LENGTH_EMAIL)
    username = serializers.CharField(
        max_length=MAX_LENGTH_USERNAME,
        validators=(validate_username,),
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Проверяет занятость username и соответствие email."""
        username = data['username']
        email = data['email']
        # Один запрос вместо exists() + get(): пользователь с таким
        # username есть — сверяем email, нет — проверяем занятость email.
        user = User.objects.filter(username=username).first()
        if user is not None:
            if user.email != email:
                raise serializers.ValidationError(
                    {'username': 'Такой username уже занят.'}
                )
            return data
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {'email': 'Такой email уже зарегистрирован.'}
            )
        return data


class GetTokenSerializer(serializers.Serializer[dict[str, Any]]):
    """Сериализатор получения JWT-токена по коду подтверждения."""

    username = serializers.CharField(max_length=MAX_LENGTH_USERNAME)
    confirmation_code = serializers.CharField(
        max_length=MAX_LENGTH_CONFIRMATION_CODE,
        write_only=True,
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Проверяет username и код подтверждения."""
        try:
            user = User.objects.get(username=data['username'])
        except User.DoesNotExist:
            raise NotFound('Пользователь не найден.') from None
        code_hash = hash_confirmation_code(data['confirmation_code'])
        # compare_digest вместо != : сравнение за постоянное время,
        # без утечки числа совпавших символов через тайминги.
        if not hmac.compare_digest(user.confirmation_code, code_hash):
            raise serializers.ValidationError(MSG_WRONG_CONFIRMATION_CODE)
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer['User']):
    """Сериализатор пользователей для админских эндпоинтов /users/."""

    class Meta:
        """Настройки сериализатора User."""

        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'bio',
            'role',
        )


class UserMeSerializer(UserSerializer):
    """Сериализатор эндпоинта /users/me/."""

    class Meta(UserSerializer.Meta):
        """Настройки сериализатора /users/me/ (role только для чтения)."""

        read_only_fields = ('role',)


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
