"""Сериализаторы для регистрации, токенов, пользователей и контента.

Контент: произведения, категории, жанры, отзывы и комментарии.
"""

from typing import Any, Mapping

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from reviews.models import Category, Comment, Genre, Review, Title

from users.models import User
from users.utils import hash_confirmation_code

UserModel = get_user_model()

FORBIDDEN_USERNAME = 'me'
MSG_FORBIDDEN_USERNAME = 'Использовать имя "me" в качестве username запрещено.'
MSG_WRONG_CONFIRMATION_CODE = 'Неверный код подтверждения.'


class SignUpSerializer(serializers.Serializer[dict[str, Any]]):
    """Сериализатор самостоятельной регистрации пользователя."""
    email = serializers.EmailField(max_length=254)
    username = serializers.RegexField(
        regex=r'^[\w.@+-]+\Z',
        max_length=150,
    )

    def validate_username(self, username: str) -> str:
        """Запрещает зарезервированный username 'me'."""
        if username.lower() == FORBIDDEN_USERNAME:
            raise serializers.ValidationError(MSG_FORBIDDEN_USERNAME)
        return username

    def validate(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """Проверяет занятость username и соответствие email."""
        username = data['username']
        email = data['email']
        if UserModel.objects.filter(username=username).exists():
            user = UserModel.objects.get(username=username)
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
    username = serializers.CharField(max_length=150)
    confirmation_code = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """Проверяет username и код подтверждения."""
        try:
            user = UserModel.objects.get(username=data['username'])
        except User.DoesNotExist:
            raise NotFound('Пользователь не найден.') from None
        code_hash = hash_confirmation_code(data['confirmation_code'])
        if user.confirmation_code != code_hash:
            raise serializers.ValidationError(MSG_WRONG_CONFIRMATION_CODE)
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer[User]):
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

    def validate(self, data: Mapping[str, Any]) -> dict[str, Any]:
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


class CategorySerializer(serializers.ModelSerializer[Category]):
    """Сериализатор для работы с моделью категорий (Category)."""
    
    class Meta:
        """Настройки сериализатора Category."""
        model = Category
        fields = ('name', 'slug')


class GenreSerializer(serializers.ModelSerializer[Genre]):
    """Сериализатор для работы с моделью жанров (Genre)."""
    
    class Meta:
        """Настройки сериализатора Genre."""
        model = Genre
        fields = ('name', 'slug')


class TitleReadSerializer(serializers.ModelSerializer[Title]):
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
            'category'
        )


class TitleWriteSerializer(serializers.ModelSerializer[Title]):
    """Сериализатор для создания/обновления произведений (POST, PATCH)."""
    genre = serializers.SlugRelatedField[Genre](
        many=True,
        slug_field='slug',
        queryset=Genre.objects.all(),
    )
    category = serializers.SlugRelatedField[Category](
        slug_field='slug',
        queryset=Category.objects.all(),
    )

    class Meta:
        """Настройки сериализатора записи Title."""
        model = Title
        fields = ('id', 'name', 'year', 'description', 'genre', 'category')
