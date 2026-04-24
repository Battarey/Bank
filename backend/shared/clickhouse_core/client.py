"""Async ClickHouse клиент для бизнес-логов.

Хранит структурированные события (транзакции, операции со счетами,
аутентификация) для аналитики и мониторинга.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import clickhouse_connect
from clickhouse_connect.driver.asyncclient import AsyncClient

from shared.bootstrap import get_container

logger = logging.getLogger("clickhouse_core")

_client: AsyncClient | None = None

# DDL для таблицы бизнес-логов
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS business_events (
	id          UUID DEFAULT generateUUIDv4(),
	event_type  LowCardinality(String),
	service     LowCardinality(String),
	user_id     UUID,
	entity_id   Nullable(UUID),
	entity_type LowCardinality(Nullable(String)),
	action      LowCardinality(String),
	amount      Nullable(Decimal(18, 2)),
	currency    LowCardinality(Nullable(String)),
	status      LowCardinality(String) DEFAULT 'success',
	details     Nullable(String),
	ip_address  Nullable(String),
	created_at  DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (event_type, user_id, created_at)
TTL toDateTime(created_at) + INTERVAL 2 YEAR
SETTINGS index_granularity = 8192
"""


async def init_clickhouse() -> None:
	"""Подключение к ClickHouse и создание таблицы через контейнер."""
	container = get_container()
	settings = container.history_settings

	container._clickhouse_client = await clickhouse_connect.get_async_client(
		host=settings.HOST,
		port=settings.PORT,
		username=settings.USER,
		password=settings.PASSWORD,
		database=settings.DATABASE,
	)

	# Создаём таблицу если не существует
	await container._clickhouse_client.command(_CREATE_TABLE_SQL)

	logger.info(
		"ClickHouse подключён: %s:%s/%s",
		settings.HOST,
		settings.PORT,
		settings.DATABASE,
	)


async def close_clickhouse() -> None:
	"""Закрытие соединения с ClickHouse через контейнер."""
	container = get_container()

	if container._clickhouse_client is not None:
		try:
			await container._clickhouse_client.close()
			logger.info("ClickHouse отключён.")
		finally:
			container._clickhouse_client = None


async def insert_log_event(
	*,
	event_type: str,
	service: str,
	user_id: str,
	action: str,
	entity_id: str | None = None,
	entity_type: str | None = None,
	amount: float | None = None,
	currency: str | None = None,
	status: str = "success",
	details: str | None = None,
	ip_address: str | None = None,
	created_at: str | None = None,
) -> None:
	"""Вставить одно бизнес-событие в ClickHouse.

	Args:
		event_type: Категория события (auth, account, transaction).
		service: Имя сервиса-источника.
		user_id: UUID пользователя.
		action: Конкретное действие (login, deposit, open_account и т.д.).
		entity_id: UUID связанной сущности (счёт, транзакция).
		entity_type: Тип сущности (account, transaction).
		amount: Сумма операции.
		currency: Валюта.
		status: Результат (success, failed, blocked).
		details: Дополнительная информация.
		ip_address: IP-адрес клиента.
		created_at: ISO-время события (если не указано — текущее).
	"""
	client = get_container()._clickhouse_client

	if client is None:
		logger.warning("ClickHouse не подключён. Событие не записано.")
		return

	ts = created_at or datetime.now(UTC).isoformat()

	row = [
		[
			event_type,
			service,
			user_id,
			entity_id,
			entity_type,
			action,
			amount,
			currency,
			status,
			details,
			ip_address,
			ts,
		]
	]

	column_names = [
		"event_type",
		"service",
		"user_id",
		"entity_id",
		"entity_type",
		"action",
		"amount",
		"currency",
		"status",
		"details",
		"ip_address",
		"created_at",
	]

	try:
		await client.insert(
			table="business_events",
			data=row,
			column_names=column_names,
		)
	except Exception:
		logger.exception("Не удалось записать событие в ClickHouse")


async def ping_clickhouse() -> bool:
	"""Проверить доступность ClickHouse через контейнер."""
	client = get_container()._clickhouse_client
	if client is None:
		return False
	return await client.ping()


__all__ = ["close_clickhouse", "init_clickhouse", "insert_log_event", "ping_clickhouse"]
