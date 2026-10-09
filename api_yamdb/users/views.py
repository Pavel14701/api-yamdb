"""Представления API: регистрация, выдача токена, пользователи.

Вьюхи пользователей живут в своём доменном приложении users;
сериализаторы домена — в users/serializers.py, общие permissions
— в api/.
"""

from http import HTTPStatus

from django.contrib.auth.models import AnonymousUser
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken

from api.permissions import IsAdmin
from users.exceptions import EmailDeliveryError
from users.models import User
from users.serializers import (
    GetTokenSerializer,
    SignUpSerializer,
    UserMeSerializer,
    UserSerializer,
)
from users.services import signup_user


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
    # Бизнес-логика (пользователь + код + доставка письма, включая
    # гонки параллельных регистраций) — в users.services. ValidationError
    # о занятых username/email сервис поднимает сам — DRF обработает
    # её в 400 без дополнительного кода.
    try:
        signup_user(
            serializer.validated_data['username'],
            serializer.validated_data['email'],
        )
    except EmailDeliveryError:
        # Отказ доставки — ожидаемый сбой внешнего сервиса (SMTP),
        # а не ошибка сервера: честный SERVICE_UNAVAILABLE вместо
        # сырого 500. Создание аккаунта откатилось; повторный запрос
        # создаст его заново и вышлет код.
        return Response(
            {
                'detail': 'Не удалось отправить письмо с кодом, '
                'повторите запрос позже.'
            },
            status=HTTPStatus.SERVICE_UNAVAILABLE,
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


def _get_auth_user(request: Request) -> Response | User:
    """Возвращает User или Response с 401 для сужения типа request.user."""
    user = request.user
    if isinstance(user, AnonymousUser):
        # Недостижимо: на экшенах стоит permission IsAuthenticated,
        # но проверка нужна для сужения типа request.user до User.
        return Response(
            {'detail': 'Требуется аутентификация.'},
            status=HTTPStatus.UNAUTHORIZED,
        )
    return user


class UserViewSet(viewsets.ModelViewSet[User]):
    """Вьюсет пользователей: управление составом и ролями юзеров.

    Полный доступ — только у администратора. PUT-запросы не
    предусмотрены спецификацией и возвращают 405.
    """

    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = (IsAdmin,)
    # Пользователь ищется по username, а не по id.
    lookup_field = 'username'
    filter_backends = (SearchFilter,)
    search_fields = ('username',)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    @action(
        detail=False,
        methods=('get',),
        url_path='me',
        url_name='me',
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request: Request) -> Response:
        """Профиль текущего пользователя (GET /users/me/).

        Любой авторизованный пользователь может посмотреть свои данные.
        PUT не предусмотрен (см. http_method_names).
        """
        auth = _get_auth_user(request)
        if isinstance(auth, Response):
            return auth
        serializer = UserMeSerializer(auth)
        return Response(serializer.data, status=HTTPStatus.OK)

    @me.mapping.patch
    def update_me(self, request: Request) -> Response:
        """Изменение профиля текущим пользователем (PATCH /users/me/).

        Поле role доступно только для чтения (см. UserMeSerializer).
        Каждый HTTP-метод повешен на своё действие вьюсета —
        без ручной маршрутизации по request.method (замечание ревью).
        """
        auth = _get_auth_user(request)
        if isinstance(auth, Response):
            return auth
        serializer = UserMeSerializer(
            auth,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=HTTPStatus.OK)
