"""Кастомные исключения доменного приложения users."""


class EmailDeliveryError(Exception):
    """Письмо с кодом подтверждения не доставлено после всех ретраев.

    Ожидаемое исключение: вьюха ловит его и отвечает
    SERVICE_UNAVAILABLE, не оставляя клиента с сырым 500.
    Исходная ошибка SMTP/сети доступна через __cause__
    (raise ... from), попытки — в атрибуте attempts.
    """

    def __init__(self, email: str, attempts: int) -> None:
        """Сохраняет адрес и число попыток для сообщения и логов."""
        self.email = email
        self.attempts = attempts
        super().__init__(
            f'Не удалось доставить письмо на {email} '
            f'за {attempts} попыток',
        )
