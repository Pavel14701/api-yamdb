"""Права доступа для API YaMDb."""

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAdmin(permissions.BasePermission):
    """Разрешает доступ только администраторам.

    Суперпользователь всегда считается администратором, даже если
    его роль в базе изменена.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Проверяет, авторизован ли пользователь и является ли админом."""
        user = request.user
        return user.is_authenticated and (
            user.role == 'admin' or user.is_superuser
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """Чтение — всем (в том числе анонимам), изменение — только админу.

    Используется для ресурсов-справочников: категории, жанры,
    произведения.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Разрешает небезопасные методы только администратору."""
        if request.method in permissions.SAFE_METHODS:
            return True
        return IsAdmin().has_permission(request, view)


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
        obj: Any,
    ) -> bool:
        """Проверяет права на конкретный объект (отзыв или комментарий)."""
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return user.is_authenticated and (
            obj.author == user
            or user.role == 'moderator'
            or user.role == 'admin'
            or user.is_superuser
        )
