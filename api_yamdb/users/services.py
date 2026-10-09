"""Бизнес-логика регистрации пользователя (без HTTP-слоя).

Обычные функции, а не классы: состояние не нужно (KISS).
Модуль не зависит от запросов и ответов — используется вьюхой
и тестируется напрямую, без клиента.
"""

import logging
import smtplib
import time
from typing import Final

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from users.codes import generate_confirmation_code, hash_confirmation_code
from users.exceptions import EmailDeliveryError
from users.models import User

logger = logging.getLogger(__name__)

# Ретраи доставки письма: число попыток и базовая задержка
# (растёт экспоненциально: backoff, backoff * 2, backoff * 4 ...).
EMAIL_MAX_ATTEMPTS: Final = 3
EMAIL_RETRY_BACKOFF: Final = 0.2

# smtplib.SMTPException назван явно, хотя и наследуется от OSError:
# при изменении иерархии исключений stdlib ретраи не потеряются
# (замечание ревью).
_RETRYABLE_MAIL_ERRORS = (ConnectionError, smtplib.SMTPException, OSError)

MSG_USERNAME_TAKEN = 'Такой username уже занят.'
MSG_EMAIL_TAKEN = 'Такой email уже зарегистрирован.'


def signup_user(username: str, email: str) -> User:
    """Создаёт пользователя и доставляет ему код подтверждения.

    Возвращает пользователя (код наружу не отдаётся — он уходит
    только на email). Конфликты уникальности поднимают DRF
    ValidationError (вьюха отдаст 400), отказ доставки —
    EmailDeliveryError (вьюха отдаст 503).

    Гонки параллельных регистраций обработаны:
    - get_or_create сам разрешает гонку создания по username
      (повторный get после IntegrityError);
    - гонка уникального email у РАЗНЫХ username доходит до нас
      IntegrityError'ом и превращается в ValidationError;
    - select_for_update сериализует повторные регистрации одного
      аккаунта: обновление хэша выполняется под блокировкой строки.

    Письмо отправляется ПОСЛЕ коммита транзакции (замечание ревью:
    код, отправленный до коммита, при откате становится «отозванным»
    — получатель держит код, которого нет в БД). Схема двухфазная:
    фаза 1 (atomic) — get_or_create, блокировка строки, обновление
    хэша, коммит; фаза 2 — хэш перечитывается из БД, и если
    параллельный signup уже перезаписал код, наш экземпляр отозван
    и письмо не отправляется (свой код доставит параллельный запрос).
    Осознанные компромиссы:
    - между перечитыванием и SMTP остаётся микрогонка, но её окно —
      миллисекунды, а не секунды SMTP-ретраев (отправка внутри
      транзакции, как раньше, эту микрогонку не устраняет, зато
      оставляет проблему отозванных кодов);
    - сбой доставки больше не откатывает создание аккаунта — он уже
      закоммичен: повторный signup регенерирует код и повторяет
      доставку (как и было до переноса письма под транзакцию).
    """
    with transaction.atomic():
        try:
            User.objects.get_or_create(
                username=username,
                defaults={'email': email},
            )
        except IntegrityError:
            # Сюда попадает только гонка email-уникальности:
            # конфликт username get_or_create разрешает
            # внутренним повторным get.
            raise ValidationError({'email': MSG_EMAIL_TAKEN}) from None
        # Блокировка строки: конкурирующие регистрации одного
        # аккаунта выполняют блок строго последовательно.
        user = User.objects.select_for_update().get(username=username)
        if user.email != email:
            # Аккаунт создан между проверкой сериализатора и текущим
            # запросом (параллельный signup или админ) с другим
            # email — чужой аккаунт не используем и код на чужой
            # адрес не шлём.
            raise ValidationError({'username': MSG_USERNAME_TAKEN})
        code = generate_confirmation_code()
        user.confirmation_code = hash_confirmation_code(code)
        # Точечный UPDATE: не перезаписать поля, изменённые админом.
        user.save(update_fields=('confirmation_code',))
        committed_hash = user.confirmation_code
    # Фаза 2 — после коммита: хэш мог быть перезаписан параллельной
    # регистрацией между нашим коммитом и перечитыванием.
    if _stored_confirmation_hash(user.pk) != committed_hash:
        logger.info(
            'Код для %s перезаписан параллельной регистрацией, '
            'письмо не отправляется.',
            user.email,
        )
        return user
    send_confirmation_code(user, code)
    return user


def _stored_confirmation_hash(user_pk: int) -> str:
    """Актуальный хэш кода из БД (перечитывание после коммита)."""
    fresh = User.objects.only('confirmation_code').get(pk=user_pk)
    return fresh.confirmation_code


def send_confirmation_code(user: User, code: str) -> None:
    """Отправляет исходный код подтверждения на email пользователя.

    Сетевые сбои SMTP ретраятся с экспоненциальной задержкой;
    после исчерпания попыток поднимается EmailDeliveryError
    с исходной ошибкой в __cause__.
    """
    last_error: BaseException | None = None
    for attempt in range(1, EMAIL_MAX_ATTEMPTS + 1):
        try:
            _send_code_email(user.email, code)
        except _RETRYABLE_MAIL_ERRORS as error:
            last_error = error
            logger.warning(
                'Письмо для %s не отправлено (попытка %d/%d): %s',
                user.email,
                attempt,
                EMAIL_MAX_ATTEMPTS,
                error,
            )
            if attempt < EMAIL_MAX_ATTEMPTS:
                time.sleep(EMAIL_RETRY_BACKOFF * 2 ** (attempt - 1))
        else:
            return
    raise EmailDeliveryError(user.email, EMAIL_MAX_ATTEMPTS) from last_error


def _send_code_email(email: str, code: str) -> None:
    """Одна попытка отправки письма с кодом."""
    send_mail(
        subject='YaMDb: код подтверждения',
        message=f'Ваш код подтверждения: {code}',
        # Адрес отправителя берём из настроек, а не дублируем локально.
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=(email,),
    )
