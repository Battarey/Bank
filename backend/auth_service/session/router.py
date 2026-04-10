"""Роутер управления сессиями и блокировки аккаунта."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from shared.internal_auth import require_user_id
from shared.schemas import MessageResponse

from ..uow import AuthUnitOfWork, get_uow
from . import service

router = APIRouter(tags=["auth-sessions"])


@router.delete(
	"/sessions/current",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Завершить текущую сессию (Logout)",
)
async def logout(
	x_session_token: str = Header(..., alias="X-Session-Token"),
):
	"""Удаляет текущий сессионный токен из Redis.

	Args:
		x_session_token: Активный токен сессии из заголовка.

	Returns:
		MessageResponse: Подтверждение завершения сеанса.
	"""
	await service.logout(x_session_token)
	return MessageResponse(message="Сеанс успешно завершён.")


@router.delete(
	"/sessions",
	# response_model=schemas.MessageResponse,
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Завершить все сессии пользователя",
)
async def logout_all(
	user_id: UUID = Depends(require_user_id),
):
	"""Отзывает все сессионные токены, выданные данному пользователю.

	Args:
		user_id: ID пользователя из текущей сессии.

	Returns:
		MessageResponse: Подтверждение сброса всех сессий.
	"""
	await service.logout_all(user_id)
	return MessageResponse(message="Все активные сессии завершены.")


@router.post(
	"/sessions/me/block",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Самоблокировка аккаунта",
)
async def self_block(
	user_id: UUID = Depends(require_user_id),
	uow: AuthUnitOfWork = Depends(get_uow),
):
	"""Блокирует аккаунт пользователя по его инициативе.

	Замораживает счета и завершает все сессии. Восстановление доступа
	возможно только через процедуру разблокировки.

	Args:
		user_id: ID пользователя из текущей сессии.
		uow: Unit of Work для управления транзакцией и событиями.

	Returns:
		MessageResponse: Подтверждение блокировки и завершения сессий.
	"""
	await service.self_block(uow, user_id)
	return MessageResponse(message="Аккаунт заблокирован. Все сессии завершены.")
