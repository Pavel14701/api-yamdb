"""Конфигурация проекта YaMDb.

Патч django-stubs-ext делает классы Django и DRF дженериками в рантайме,
чтобы аннотации вида UserAdmin[User], ModelSerializer[User] и т.п.,
используемые для строгой типизации (mypy), работали при обычном запуске.
"""

from django_stubs_ext import monkeypatch

monkeypatch()
