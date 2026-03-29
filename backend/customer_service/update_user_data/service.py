"""Бизнес-логика обновления данных пользователя (ФИО, паспорт, контакты)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models, schemas
from shared.utils.normalize import normalize_email, normalize_name, normalize_phone
from shared.utils.security import get_blind_index

from ..repository import CustomerRepository
from ..exceptions import (
	UpdateDataConflict,
	UpdateDataEmpty,
	UpdateDataError,
	UpdateDataNotFound,
)


async def _get_active_user(repo: CustomerRepository, user_id: UUID) -> models.User:
	"""Возвращает активного пользователя для редактирования.

	Args:
		repo: Репозиторий клиентов.
		user_id: ID пользователя.

	Returns:
		User: Объект пользователя.

	Raises:
		UpdateDataNotFound: Если пользователь не найден.
		UpdateDataError: Если пользователь не в статусе active.
	"""
	user = await repo.get_active_user(user_id)
	if user.status != "active":
		raise UpdateDataError(
			f"Обновление данных запрещено: текущий статус пользователя '{user.status}'."
		)
	return user


async def update_personal_data(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PersonalDataUpdate,
) -> schemas.PersonalDataResponse:
	"""Обновляет ФИО пользователя.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		payload: Новые данные ФИО.

	Returns:
		PersonalDataResponse: Обновлённые данные.

	Raises:
		UpdateDataEmpty: Если не передано ни одного поля.
		UpdateDataNotFound: Если профиль не найден.
	"""
	repo = CustomerRepository(session)
	fields = payload.model_dump(exclude_unset=True)
	if not fields:
		raise UpdateDataEmpty("Необходимо передать хотя бы одно поле для обновления.")

	await _get_active_user(repo, user_id)
	
	record = await repo.get_personal_data(user_id)
	if record is None:
		raise UpdateDataNotFound("Персональные данные (профиль) не найдены.")

	# Нормализация
	for key in ["last_name", "first_name", "middle_name"]:
		if key in fields:
			fields[key] = normalize_name(fields[key])

	for attr, value in fields.items():
		setattr(record, attr, value)

	await repo.commit()
	await repo.refresh(record)
	
	return schemas.PersonalDataResponse.model_validate(record)


async def replace_passport(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PassportPayload,
) -> schemas.PassportResponse:
	"""Полная замена паспортных данных клиента.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		payload: Новые данные паспорта.

	Returns:
		PassportResponse: Обновлённый паспорт.

	Raises:
		UpdateDataConflict: Если новый паспорт уже используется.
	"""
	repo = CustomerRepository(session)
	await _get_active_user(repo, user_id)
	
	record = await repo.get_passport(user_id)
	if record is None:
		raise UpdateDataNotFound("Паспортные данные профиля не найдены.")

	# Нормализация и проверка уникальности
	p_hash = get_blind_index(f"{payload.series}{payload.number}")
	await repo.check_passport_unique(p_hash, exclude_client_id=user_id)

	# Обновление полей
	for attr, value in payload.model_dump().items():
		setattr(record, attr, value)
	record.passport_hash = p_hash

	try:
		await repo.commit()
	except IntegrityError as exc:
		await repo.rollback()
		raise UpdateDataConflict("Паспорт с такими данными уже зарегистрирован.") from exc
		
	await repo.refresh(record)
	return schemas.PassportResponse.model_validate(record)


async def update_contacts(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.ContactsUpdate,
) -> schemas.ContactsResponse:
	"""Частичное обновление контактов (Email, телефон).

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		payload: Обновляемые поля контактов.

	Returns:
		ContactsResponse: Обновлённый набор контактов.
	"""
	repo = CustomerRepository(session)
	fields = payload.model_dump(exclude_unset=True)
	if not fields:
		raise UpdateDataEmpty("Необходимо передать email или телефон.")

	await _get_active_user(repo, user_id)
	
	record = await repo.get_contact(user_id)
	if record is None:
		raise UpdateDataNotFound("Контактные данные профиля не найдены.")

	# Нормализация и расчет хешей
	email_hash = get_blind_index(normalize_email(fields["email"])) if "email" in fields else None
	phone_hash = get_blind_index(normalize_phone(fields["phone"])) if "phone" in fields else None

	# Проверка уникальности
	await repo.check_contacts_unique(
		email_hash=email_hash, 
		phone_hash=phone_hash, 
		exclude_client_id=user_id
	)

	# Применяем изменения
	if "email" in fields:
		record.email = normalize_email(fields["email"])
		record.email_hash = email_hash
	if "phone" in fields:
		record.phone = normalize_phone(fields["phone"])
		record.phone_hash = phone_hash

	try:
		await repo.commit()
	except IntegrityError as exc:
		await repo.rollback()
		raise UpdateDataConflict("Конфликт уникальности контактов.") from exc

	await repo.refresh(record)
	return schemas.ContactsResponse.model_validate(record)
