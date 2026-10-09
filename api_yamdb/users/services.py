"""Бизнес-логика регистрации пользователя (без HTTP-слоя).

Обычные функции, а не классы: состояние не нужно (KISS).
Модуль не зависит от запросов и ответов — используется вьюхой
и тестируется напрямую, без клиента.
"""

import logging
import time
from typing import Final

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from users.codes import generate_confirmation_code, hash_confirmation_code
from users.exceptions import EmailDeliveryError
from users.models import User

logger = logging.getLogger(__name__)

# Ретраи доставки письма: число попыток и базовая задержка
# (растёт экспоненциально: backoff, backoff * 2, backoff * 4 ...).
EMAIL_MAX_ATTEMPTS: Final = 3
EMAIL_RETRY_BACKOFF: Final = 0.2

# Письмо шлём снаружи транзакции: медленный SMTP не должен держать
# блокировки БД (антипаттерн «почта внутри atomic»). OSError
# покрывает и smtplib.SMTPException (наследуется от OSError),
# и ConnectionError.
_RETRYABLE_MAIL_ERRORS = (ConnectionError, OSError)


def signup_user(username: str, email: str) -> tuple[User, str]:
    """Создаёт пользователя или находит существующего по username.

    Существующий пользователь гарантированно имеет тот же email —
    это проверяет SignUpSerializer до вызова. Генерирует новый код
    подтверждения: в БД храним хэш (update_fields — точечный
    UPDATE, чтобы не перезаписать поля, изменённые админом
    параллельно), исходный код возвращаем для отправки.

    Обе операции — под transaction.atomic: без транзакции это два
    отдельных авто-коммита, и сбой UPDATE оставлял бы в БД
    пользователя без кода подтверждения.
    """
    with transaction.atomic():
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'email': email},
        )
        code = generate_confirmation_code()
        user.confirmation_code = hash_confirmation_code(code)
        user.save(update_fields=('confirmation_code',))
    return user, code


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
