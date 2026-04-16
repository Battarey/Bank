"""Роутер разблокировки аккаунта: запрос кода и подтверждение."""

from fastapi import APIRouter, Depends, status

from shared.schemas import MessageResponse, RequestUnlockRequest, UnlockRequest

from ..core.uow import AuthUnitOfWork, get_uow
from ..services import unlock as service

router = APIRouter(tags=["auth-unlock"])


@router.post(
	"/unlock-codes",
	response_model=MessageResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Запросить код восстановления доступа",
)
async def request_unlock(
	body: RequestUnlockRequest,
	uow: AuthUnitOfWork = Depends(get_uow),
):
	"""Генерирует 6-значный код и отправляет его на привязанный Email пользователя.

	Args:
		body: Номер телефона пользователя для поиска аккаунта.
		uow: Unit of Work для управления транзакцией и событиями.

	Returns:
		MessageResponse: Подтверждение отправки кода.
	"""
	await service.request_unlock(uow, body.phone)
	return MessageResponse(message="Код восстановления отправлен на ваш Email.")


@router.post(
	"/unlock-codes/verifications",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Подтвердить восстановление и сменить PIN",
)
async def confirm_unlock(
	body: UnlockRequest,
	uow: AuthUnitOfWork = Depends(get_uow),
):
	"""Проверяет код и устанавливает новый PIN-код доступа.

	Args:
		body: Данные для восстановления (телефон, код, новый PIN).
		uow: Unit of Work для управления транзакцией и событиями.

	Returns:
		MessageResponse: Подтверждение успешного восстановления доступа.
	"""
	await service.confirm_unlock(uow, body.phone, body.code, body.new_pin)
	return MessageResponse(message="Доступ успешно восстановлен. Используйте новый PIN для входа.")
