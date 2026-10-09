"""Регистрация модели пользователя в админ-зоне."""

from typing import TypedDict

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest

from users.models import User

# Зачем TypedDict: проект проверяется mypy в строгом режиме, а
# django-stubs типизирует секции fieldsets как TypedDict (приватный
# _FieldOpts: обязательный ключ fields, опциональные classes и
# description). Обычный dict[str, Any] такую проверку не проходит:
# TypedDict — это «словарь с заранее известным набором ключей»,
# mypy проверяет его статически; в рантайме это самый обычный dict,
# ничего нового Django тут не требует. Приватный _FieldOpts
# импортировать нельзя, поэтому объявляем свой с той же структурой.


class _YaMDbFieldOpts(TypedDict):
    """Опции одной секции fieldsets (аналог _FieldOpts из django-stubs).

    В рантайме — обычный dict вида {'fields': (...)}. Класс нужен
    только mypy: он гарантирует, что ключ fields указан и содержит
    кортеж имён полей модели.
    """

    fields: tuple[str, ...]


# Секция карточки пользователя с полями YaMDb. Вынесена в константу,
# чтобы не собирать словарь внутри метода: секция одна, используется
# в get_fieldsets ниже. В рантайме это просто
# ('YaMDb', {'fields': ('role', 'bio', 'confirmation_code')}) —
# стандартный формат fieldsets из документации Django.
YAMDB_FIELDSET: tuple[str, _YaMDbFieldOpts] = (
    'YaMDb',
    {'fields': ('role', 'bio', 'confirmation_code')},
)


@admin.register(User)
class YamdbUserAdmin(UserAdmin[User]):
    """Настройка отображения пользователей в админ-зоне."""

    list_display = (
        'username',
        'email',
        'role',
        'first_name',
        'last_name',
    )
    search_fields = ('username', 'email')
    list_filter = ('role',)

    # Директива type: ignore[override] на строке def ниже обязательна:
    # тип возврата структурно совпадает с типом из django-stubs, но там
    # он объявлен через приватный псевдоним (список ИЛИ кортеж
    # секций), который нельзя импортировать, и mypy формально не
    # считает наш кортеж его подтипом. Поведение в рантайме от
    # этого не меняется.

    def get_fieldsets(  # type: ignore[override]
        self,
        request: HttpRequest,
        obj: User | None = None,
    ) -> tuple[tuple[str | None, _YaMDbFieldOpts], ...]:
        """Дополняет стандартные секции админки секцией YaMDb.

        Переопределяем метод, а не атрибут fieldsets: у родителя
        вложенные dict'ы общие, конкатенация на уровне класса
        делала бы их общими и с нами (мутируешь в одном месте —
        меняется в другом). Здесь родительская конфигурация не
        копируется и не меняется, секция добавляется только
        в результате вызова.
        """
        return (*super().get_fieldsets(request, obj), YAMDB_FIELDSET)
