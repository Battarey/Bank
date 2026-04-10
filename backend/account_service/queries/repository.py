"""Репозиторий для высокопроизводительного чтения данных счетов (CQRS Query Layer)."""

from uuid import UUID

from shared.database_core.base_query_repository import BaseQueryRepository
from shared.schemas.bank_account import AccountResponse


class AccountQueryRepository(BaseQueryRepository):
	"""Репозиторий для чтения данных банковских счетов через сырой SQL."""

	async def list_by_user_with_total(self, user_id: UUID) -> tuple[list[AccountResponse], int]:
		"""Возвращает список счетов пользователя с общим количеством.

		Args:
			user_id: ID владельца счетов.

		Returns:
			tuple[list[AccountResponse], int]: Список счетов и их общее количество.
		"""
		params = {"client_id": user_id}

		# Оптимизированный запрос данных (обходим ORM)
		data_query = """
			SELECT 
				id, client_id, account_number, type, currency, 
				balance, status, opened_at, closed_at, 
				frozen_by, frozen_at, freeze_reason
			FROM bank_accounts
			WHERE client_id = :client_id
			ORDER BY opened_at DESC
		"""

		# Запрос общего количества
		count_query = "SELECT COUNT(*) FROM bank_accounts WHERE client_id = :client_id"

		rows = await self._fetch_rows(data_query, params)
		total = await self._get_total(count_query, params)

		return self._map_to_schemas(rows, AccountResponse), total

	async def get_by_id_raw(self, user_id: UUID, account_id: UUID) -> AccountResponse | None:
		"""Возвращает данные конкретного счета пользователя без оверхеда ORM.

		Args:
			user_id: ID владельца.
			account_id: ID искомого счета.

		Returns:
			AccountResponse | None: Данные счета или None.
		"""
		params = {"client_id": user_id, "account_id": account_id}
		query = """
			SELECT 
				id, client_id, account_number, type, currency, 
				balance, status, opened_at, closed_at, 
				frozen_by, frozen_at, freeze_reason
			FROM bank_accounts
			WHERE id = :account_id AND client_id = :client_id
		"""
		row = await self._fetch_one(query, params)
		return self._map_to_schema(row, AccountResponse) if row else None
