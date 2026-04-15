"""Сервис для логирования событий."""

import asyncio
import logging

from ..repositories.log import ClickHouseRepository, PostgresHistoryRepository
from ..core.schemas import LogEvent

logger = logging.getLogger("log_service")


class LogService:
	"""Сервис для обработки логов."""

	def __init__(
		self,
		postgres_repo: PostgresHistoryRepository,
		clickhouse_repo: ClickHouseRepository,
	):
		self.postgres_repo = postgres_repo
		self.clickhouse_repo = clickhouse_repo

	async def process_log(self, event: LogEvent) -> None:
		"""Обрабатывает одно событие логирования.

		Записывает данные параллельно в Postgres (аудит) и Clickhouse (аналитика).
		"""
		msg_type = event.type
		payload = event.payload

		# Записываем параллельно в оба хранилища
		results = await asyncio.gather(
			self.postgres_repo.save_action(payload),
			self.clickhouse_repo.save_event(msg_type, payload),
			return_exceptions=True,
		)

		# Обработка исключений из репозиториев
		for i, result in enumerate(results):
			if isinstance(result, Exception):
				store_name = "postgres_history" if i == 0 else "ClickHouse"
				logger.error(
					"Ошибка записи в %s для type=%s: %s",
					store_name,
					msg_type,
					result,
				)
