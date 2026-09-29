"""Права доступа для отзывов и комментариев."""

from rest_framework import permissions

from users.models import User


class IsAuthorOrModeratorOrAdminOrReadOnly(permissions.BasePermission):
    """
    Права доступа для отзывов и комментариев.

    - Анонимные пользователи могут только читать (SAFE_METHODS).
    - Аутентифицированные пользователи могут создавать.
    - Редактировать и удалять могут авторы, модераторы и администраторы.
    """

    def has_permission(self, request, view):
        """Проверка прав на уровне общего запроса к эндпоинту."""
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        """Проверка прав на уровне конкретного объекта(отзыва/комментария)."""
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            obj.author == request.user
            or getattr(request.user, 'role', None) == User.MODERATOR
            or getattr(request.user, 'is_admin', False)
            or request.user.is_superuser
        )
