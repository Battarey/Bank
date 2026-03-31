"""Репозиторий для высокопроизводительного чтения истории транзакций (CQRS Query Layer)."""

from typing import Any
from uuid import UUID

from shared.database_core.base_query_repository import BaseQueryRepository
from shared.schemas.transaction import TransactionResponse


class TransactionQueryRepository(BaseQueryRepository):
	"""Репозиторий для работы с историей транзакций через сырой SQL."""

	async def get_history_with_total(
		self,
		account_id: UUID,
		limit: int = 20,
		offset: int = 0,
		tx_type: str | None = None,
		direction: str | None = None,
	) -> tuple[list[TransactionResponse], int]:
		"""Получает историю транзакций и общее количество за один/два быстрых запроса.

		Args:
			account_id: ID счёта.
			limit: Лимит записей.
			offset: Смещение.
			tx_type: Фильтр по типу.
			direction: Фильтр по направлению.

		Returns:
			tuple[list[TransactionResponse], int]: Список транзакций и total count.
		"""
		params: dict[str, Any] = {
			"account_id": account_id,
			"limit": limit,
			"offset": offset,
		}

		# Базовая фильтрация
		where_clauses = ["account_id = :account_id"]

		if tx_type:
			where_clauses.append("type = :tx_type")
			params["tx_type"] = tx_type
		
		if direction:
			where_clauses.append("direction = :direction")
			params["direction"] = direction

		where_sql = " AND ".join(where_clauses)

		# Запрос данных (используем сырой SQL для обхода оверхеда ORM)
		data_query = f"""
			SELECT 
				id, account_id, type, amount, created_at, 
				description, related_account_id, direction, 
				status, balance_before, balance_after, external_ref
			FROM transactions
			WHERE {where_sql}
			ORDER BY created_at DESC
			LIMIT :limit OFFSET :offset
		"""

		# Запрос общего количества для пагинации
		count_query = f"SELECT COUNT(*) FROM transactions WHERE {where_sql}"

		rows = await self._fetch_rows(data_query, params)
		total = await self._get_total(count_query, params)

		return self._map_to_schemas(rows, TransactionResponse), total
