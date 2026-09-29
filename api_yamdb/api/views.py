"""Представления API: регистрация, выдача токена, пользователи."""

from http import HTTPStatus

from django.contrib.auth.models import AnonymousUser
from django.core.mail import send_mail
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken

from api.permissions import IsAdmin
from api.serializers import (
    GetTokenSerializer,
    SignUpSerializer,
    UserMeSerializer,
    UserSerializer,
)
from users.models import User
from users.utils import generate_confirmation_code, hash_confirmation_code

DEFAULT_FROM_EMAIL = 'noreply@yamdb.fake'


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request: Request) -> Response:
    """Самостоятельная регистрация пользователя (POST /auth/signup/).

    Создаёт нового пользователя или находит существующего
    (по паре username + email), генерирует новый код подтверждения
    и отправляет его на указанный email. Повторный запрос с теми же
    данными высылает письмо заново — это позволяет получить код
    пользователю, созданному администратором.
    """
    serializer = SignUpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = serializer.validated_data['username']
    email = serializer.validated_data['email']
    # Пользователь существует только с тем же email — это проверено
    # в сериализаторе, поэтому просто находим или создаём его.
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={'email': email},
    )
    # В базе храним хэш кода, в письме отправляем исходный код.
    code = generate_confirmation_code()
    user.confirmation_code = hash_confirmation_code(code)
    user.save()
    send_mail(
        subject='YaMDb: код подтверждения',
        message=f'Ваш код подтверждения: {code}',
        from_email=DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    return Response(serializer.data, status=HTTPStatus.OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def obtain_token(request: Request) -> Response:
    """Выдача JWT-токена (POST /auth/token/).

    Принимает username и confirmation_code. Повторная передача
    кода обновляет access-токен.
    """
    serializer = GetTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    token = AccessToken.for_user(serializer.validated_data['user'])
    return Response({'token': str(token)}, status=HTTPStatus.OK)


class UsersPagination(PageNumberPagination):
    """Пагинация только для списка пользователей.

    Настраивается локально, чтобы не влиять на другие ресурсы API.
    """

    page_size = 10


class UserViewSet(viewsets.ModelViewSet[User]):
    """Вьюсет пользователей: управление составом и ролями юзеров.

    Полный доступ — только у администратора. PUT-запросы не
    предусмотрены спецификацией и возвращают 405.
    """

    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = (IsAdmin,)
    # Пользователь ищется по username, а не по id.
    lookup_field = 'username'
    filter_backends = (SearchFilter,)
    search_fields = ('username',)
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    pagination_class = UsersPagination

    @action(
        detail=False,
        methods=['get', 'patch'],
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request: Request) -> Response:
        """Профиль текущего пользователя (GET/PATCH /users/me/).

        Любой авторизованный пользователь может посмотреть и
        изменить свои данные, кроме поля role — оно доступно
        только для чтения.
        """
        user = request.user
        if isinstance(user, AnonymousUser):
            # Недостижимо: на экшене стоит permission IsAuthenticated,
            # но проверка нужна для сужения типа request.user до User.
            return Response(
                {'detail': 'Требуется аутентификация.'},
                status=HTTPStatus.UNAUTHORIZED,
            )
        if request.method == 'PATCH':
            serializer = UserMeSerializer(
                user,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = UserMeSerializer(user)
        return Response(serializer.data, status=HTTPStatus.OK)
