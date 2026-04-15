from uuid import UUID

from shared import schemas

from ..uow import TransactionUnitOfWork


async def list_transactions(
	uow: TransactionUnitOfWork,
	user_id: UUID,
	account_id: UUID,
	*,
	limit: int = 20,
	offset: int = 0,
	tx_type: str | None = None,
	direction: str | None = None,
) -> tuple[list[schemas.TransactionResponse], int]:
	"""Возвращает историю операций по счёту с поддержкой пагинации и фильтрации.

	Args:
		uow: Unit of Work для управления транзакцией.
		user_id: ID владельца счёта (для проверки прав).
		account_id: ID счёта, историю которого нужно получить.
		limit: Количество записей на страницу (макс. 100).
		offset: Смещение (пропуск записей).
		tx_type: Опциональный фильтр по типу (deposit, withdrawal, transfer).
		direction: Опциональный фильтр по направлению (incoming, outgoing).

	Returns:
		tuple[Sequence[Transaction], int]: Список транзакций и общее количество (total_count).
	"""
	async with uow:
		# 1. Проверка принадлежности счёта
		account = await uow.transactions.get_account(account_id)
		if account.client_id != user_id:
			from ..exceptions import AccountNotFound

			raise AccountNotFound("Счёт не принадлежит вам.")

		# 2. Получение данных через репозиторий чтения (CQRS Query Layer)
		return await uow.history_query.get_history_with_total(
			account_id,
			limit=limit,
			offset=offset,
			tx_type=tx_type,
			direction=direction,
		)
