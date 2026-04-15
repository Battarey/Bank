"""HTTP-клиент для вызова Security Service (AML-проверка)."""

import logging
from decimal import Decimal
from uuid import UUID

import httpx

from shared.bootstrap import get_container

# Обновленный путь к конфигу
from ..core.config import TransactionSettings

logger = logging.getLogger("transaction_service")


def _get_settings() -> TransactionSettings:
	"""Получает специфические настройки для сервиса транзакций."""
	return get_container().settings


_client: httpx.AsyncClient | None = None


async def connect() -> None:
	"""Создаёт httpx-клиент для Security Service."""
	global _client
	settings = _get_settings()
	_client = httpx.AsyncClient(base_url=settings.SECURITY_SERVICE_URL, timeout=10.0)
	logger.info("Security client подключён: %s", settings.SECURITY_SERVICE_URL)


async def disconnect() -> None:
	"""Закрывает httpx-клиент."""
	global _client
	if _client is not None:
		await _client.aclose()
		_client = None
		logger.info("Security client отключён.")


from shared.schemas.security import SecurityCheckRequest


async def check_transaction(
	account_id: UUID,
	tx_type: str,
	amount: Decimal,
	currency: str,
) -> tuple[bool, list[dict]]:
	"""Проверяет pending-транзакцию у Security Service.

	Returns:
		(allowed, violations) — allowed=True если разрешено.
	"""

	if _client is None:
		logger.warning("Security client не инициализирован — пропускаем проверку")
		return True, []

	payload = SecurityCheckRequest(
		account_id=account_id,
		tx_type=tx_type,
		amount=amount,
		currency=currency,
	)

	settings = _get_settings()
	try:
		response = await _client.post(
			"/evaluations",
			json=payload.model_dump(mode="json"),
			headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
		)
		if response.status_code == 200:
			data = response.json()
			return data["allowed"], data.get("violations", [])
		else:
			logger.error("Security Service вернул %s: %s", response.status_code, response.text)
			# При ошибке security — пропускаем (fail-open)
			return True, []
	except Exception as exc:
		logger.exception("Ошибка вызова Security Service при проверке транзакции: %s", exc)
		# fail-open: не блокируем операцию при недоступности
		return True, []
