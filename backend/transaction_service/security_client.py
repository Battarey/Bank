"""HTTP-клиент для вызова Security Service (AML-проверка)."""

import logging
import os
from decimal import Decimal
from uuid import UUID

import httpx

logger = logging.getLogger("transaction_service")

SECURITY_SERVICE_URL = os.getenv("SECURITY_SERVICE_URL", "http://security_service:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

_client: httpx.AsyncClient | None = None


async def connect() -> None:
	"""Создаёт httpx-клиент для Security Service."""
	global _client  # noqa: PLW0603
	_client = httpx.AsyncClient(base_url=SECURITY_SERVICE_URL, timeout=10.0)
	logger.info("Security client подключён: %s", SECURITY_SERVICE_URL)


async def disconnect() -> None:
	"""Закрывает httpx-клиент."""
	global _client  # noqa: PLW0603
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

	try:
		response = await _client.post(
			"/check",
			json=payload.model_dump(mode="json"),
			headers={"X-Internal-Key": INTERNAL_API_KEY},
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
