"""Роутер аутентификации: вход и управление PIN-кодом."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.internal_auth import require_user_id
from shared.schemas import LoginPinRequest, LoginPinResponse, MessageResponse, SetPinRequest

from ..core.uow import AuthUnitOfWork, get_uow
from ..services import login as service

router = APIRouter(tags=["auth-sessions"])


@router.post(
	"/sessions",
	response_model=LoginPinResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Создать сессию (Вход)",
)
async def login(
	body: LoginPinRequest,
	uow: AuthUnitOfWork = Depends(get_uow),
):
	"""Аутентифицирует пользователя по номеру телефона и PIN-коду.

	Args:
		body: Номер телефона и PIN-код.
		uow: Unit of Work для управления транзакцией и событиями.

	Returns:
		LoginPinResponse: Сессионный токен, токен привязки и ID пользователя.
	"""
	session_token, refresh_token, user_id = await service.login_pin(uow, body.phone, body.pin)
	return LoginPinResponse(
		session_token=session_token,
		refresh_token=refresh_token,
		user_id=str(user_id),
	)


@router.post(
	"/sessions/quick",
	response_model=LoginPinResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Быстрый вход (по PIN)",
)
async def quick_login(
	body: schemas.QuickLoginRequest,
	uow: AuthUnitOfWork = Depends(get_uow),
):
	"""Аутентифицирует пользователя по токену привязки и PIN-коду.

	Используется для повторного входа без ввода номера телефона.
	При каждом входе токен привязки обновляется (Rotating Refresh Token).

	Args:
		body: Токен привязки и PIN-код.
		uow: Unit of Work.

	Returns:
		LoginPinResponse: Новая пара токенов и ID пользователя.
	"""
	session_token, refresh_token, user_id = await service.login_quick(uow, body.refresh_token, body.pin)
	return LoginPinResponse(
		session_token=session_token,
		refresh_token=refresh_token,
		user_id=str(user_id),
	)


@router.put(
	"/pins",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Установить/сменить PIN",
)
async def set_pin(
	body: SetPinRequest,
	user_id: UUID = Depends(require_user_id),
	uow: AuthUnitOfWork = Depends(get_uow),
):
	"""Устанавливает или обновляет PIN-код для текущего пользователя.

	Args:
		body: Модель с новым PIN-кодом (4 цифры).
		user_id: ID пользователя, полученный из сессионного токена.
		uow: Unit of Work для управления транзакцией и событиями.

	Returns:
		MessageResponse: Подтверждение успешного обновления.
	"""
	await service.set_pin(uow, user_id, body.pin)
	return MessageResponse(message="PIN-код успешно обновлён.")
