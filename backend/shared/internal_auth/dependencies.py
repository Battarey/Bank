"""Зависимости для защиты внутренних микросервисов от прямого доступа."""

import secrets
from uuid import UUID

from fastapi import Header, HTTPException, status

from shared.bootstrap import get_container


def verify_internal_key(x_internal_key: str = Header(..., alias="X-Internal-Key")) -> None:
	"""Проверяет, что запрос содержит валидный внутренний ключ от gateway.

	Ключ извлекается из глобального контейнера настроек (Pydantic Settings).
	"""
	settings = get_container().settings
	internal_key = settings.INTERNAL_API_KEY

	if not internal_key:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Сервис не сконфигурирован: INTERNAL_API_KEY не задан.",
		)
	if not secrets.compare_digest(x_internal_key, internal_key):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Недействительный внутренний ключ.",
		)


def require_user_id(x_user_id: str = Header(..., alias="X-User-ID")) -> UUID:
	"""Извлекает и валидирует X-User-ID из заголовка (для защищённых эндпоинтов)."""

	try:
		return UUID(x_user_id)
	except (ValueError, AttributeError):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Отсутствует или невалиден заголовок X-User-ID.",
		) from None
