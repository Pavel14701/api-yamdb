"""Права доступа для API YaMDb."""

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from users.models import User


class IsAdmin(permissions.BasePermission):
    """Разрешает доступ только администраторам.

    Суперпользователь всегда считается администратором, даже если
    его роль в базе изменена.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Проверяет, авторизован ли пользователь и является ли админом."""
        user = request.user
        return user.is_authenticated and (
            user.role == User.ADMIN or user.is_superuser
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """Чтение — всем (в том числе анонимам), изменение — только админу.

    Используется для ресурсов-справочников: категории, жанры,
    произведения.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Разрешает небезопасные методы только администратору."""
        return request.method in permissions.SAFE_METHODS or IsAdmin(
        ).has_permission(request, view)


class IsAuthorModeratorAdminOrReadOnly(permissions.BasePermission):
    """Права для отзывов и комментариев.

    Чтение — всем. Изменение и удаление — только автору объекта,
    модератору или администратору.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Разрешает изменения только аутентифицированным пользователям."""
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        review_or_comment: Any,
    ) -> bool:
        """Проверяет права на конкретный объект (отзыв или комментарий)."""
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return user.is_authenticated and (
            review_or_comment.author == user
            or user.role == User.MODERATOR
            or user.role == User.ADMIN
            or user.is_superuser
        )
