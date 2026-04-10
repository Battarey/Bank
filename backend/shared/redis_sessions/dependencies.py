"""Зависимости FastAPI для работы с сессионными токенами в Redis."""

from typing import Annotated
from uuid import UUID

from fastapi import Header, HTTPException, status

from . import tokens as session_tokens

SessionTokenHeader = Annotated[str, Header(..., alias="X-Session-Token")]


async def authenticate_token(token: str | None) -> dict[str, str]:
	"""Проверяет наличие и валидность токена. Возвращает данные сессии.

	Используется в gateway-middleware для аутентификации запроса.
	При успешной проверке продлевает TTL токена (скользящая экспирация).
	Выбрасывает HTTPException при отсутствии или невалидности токена.
	"""

	if not token:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Отсутствует заголовок X-Session-Token.",
		)

	session_data = await session_tokens.load_token(token)
	if session_data is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Сессионный токен недействителен или истёк.",
		)

	# Скользящая экспирация: продлеваем TTL при каждом запросе
	user_id = session_data.get("user_id")
	if user_id:
		await session_tokens.touch_token(token, UUID(user_id))

	return session_data


async def verify_session_token(
	user_id: UUID,
	session_token: SessionTokenHeader,
) -> dict[str, str]:
	"""Проверяет валидность токена и соответствие его идентификатору пользователя.

	Используется как FastAPI Depends() в эндпоинтах внутренних сервисов.
	"""

	session_data = await authenticate_token(session_token)
	if session_data.get("user_id") != str(user_id):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Токен не соответствует запрошенному пользователю.",
		)
	return session_data


__all__ = ["SessionTokenHeader", "authenticate_token", "verify_session_token"]
