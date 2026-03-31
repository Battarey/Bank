"""Бизнес-логика обновления данных пользователя (ФИО, паспорт, контакты)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from shared import models, schemas
from shared.events.base import LogEvent
from shared.utils.normalize import normalize_email, normalize_name, normalize_phone
from shared.utils.security import get_blind_index

from ..uow import CustomerUnitOfWork
from ..exceptions import (
	UpdateDataConflict,
	UpdateDataEmpty,
	UpdateDataError,
	UpdateDataNotFound,
)


async def _get_active_user(uow: CustomerUnitOfWork, user_id: UUID) -> models.User:
	"""Возвращает активного пользователя для редактирования.

	Args:
		uow: Unit of Work для доступа к репозиторию.
		user_id: ID пользователя.

	Returns:
		models.User: Объект пользователя.

	Raises:
		UpdateDataNotFound: Если пользователь не найден.
		UpdateDataError: Если пользователь не в статусе active.
	"""
	user = await uow.customers.get_active_user(user_id)
	if user.status != "active":
		raise UpdateDataError(
			f"Обновление данных запрещено: текущий статус пользователя '{user.status}'."
		)
	return user


async def update_personal_data(
	uow: CustomerUnitOfWork,
	user_id: UUID,
	payload: schemas.PersonalDataUpdate,
) -> schemas.PersonalDataResponse:
	"""Обновляет ФИО пользователя.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID пользователя.
		payload: Новые данные ФИО.

	Returns:
		schemas.PersonalDataResponse: Обновлённые данные профиля.

	Raises:
		UpdateDataEmpty: Если не передано ни одного поля для обновления.
		UpdateDataNotFound: Если профиль пользователя не найден.
		UpdateDataError: Если пользователь заблокирован или удален.
	"""
	async with uow:
		fields = payload.model_dump(exclude_unset=True)
		if not fields:
			raise UpdateDataEmpty("Необходимо передать хотя бы одно поле для обновления.")

		await _get_active_user(uow, user_id)
		
		record = await uow.customers.get_personal_data(user_id)
		if record is None:
			raise UpdateDataNotFound("Персональные данные (профиль) не найдены.")

		# Нормализация
		for key in ["last_name", "first_name", "middle_name"]:
			if key in fields:
				fields[key] = normalize_name(fields[key])

		for attr, value in fields.items():
			setattr(record, attr, value)

		# Логирование события ДО коммита
		uow.add_event(LogEvent(
			user_id=user_id,
			action="update_personal_data",
			service="customer_service",
			details=f"Обновлены поля: {', '.join(fields.keys())}",
		))

		await uow.commit()
		await uow.customers.refresh(record)
		
		return schemas.PersonalDataResponse.model_validate(record)


async def replace_passport(
	uow: CustomerUnitOfWork,
	user_id: UUID,
	payload: schemas.PassportPayload,
) -> schemas.PassportResponse:
	"""Полная замена паспортных данных клиента.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID пользователя.
		payload: Новые данные паспорта.

	Returns:
		schemas.PassportResponse: Обновлённые данные паспорта.

	Raises:
		UpdateDataNotFound: Если паспортные данные не найдены.
		UpdateDataConflict: Если новый паспорт уже зарегистрирован за другим пользователем.
	"""
	async with uow:
		await _get_active_user(uow, user_id)
		
		record = await uow.customers.get_passport(user_id)
		if record is None:
			raise UpdateDataNotFound("Паспортные данные профиля не найдены.")

		# Нормализация и проверка уникальности
		p_hash = get_blind_index(f"{payload.series}{payload.number}")
		await uow.customers.check_passport_unique(p_hash, exclude_client_id=user_id)

		# Обновление полей
		for attr, value in payload.model_dump().items():
			setattr(record, attr, value)
		record.passport_hash = p_hash

		# Логирование события ДО коммита
		uow.add_event(LogEvent(
			user_id=user_id,
			action="replace_passport",
			service="customer_service",
			details="Паспорт заменен на новый",
		))

		try:
			await uow.commit()
		except IntegrityError as exc:
			raise UpdateDataConflict("Паспорт с такими данными уже зарегистрирован.") from exc
			
		await uow.customers.refresh(record)
		return schemas.PassportResponse.model_validate(record)


async def update_contacts(
	uow: CustomerUnitOfWork,
	user_id: UUID,
	payload: schemas.ContactsUpdate,
) -> schemas.ContactsResponse:
	"""Частичное обновление контактов (Email, телефон).

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID пользователя.
		payload: Обновляемые поля контактов.

	Returns:
		schemas.ContactsResponse: Обновлённый набор контактов.

	Raises:
		UpdateDataEmpty: Если поля email и phone отсутствуют в запросе.
		UpdateDataNotFound: Если контактные данные не найдены.
		UpdateDataConflict: Если новый email или телефон уже используются.
	"""
	async with uow:
		fields = payload.model_dump(exclude_unset=True)
		if not fields:
			raise UpdateDataEmpty("Необходимо передать email или телефон.")

		await _get_active_user(uow, user_id)
		
		record = await uow.customers.get_contact(user_id)
		if record is None:
			raise UpdateDataNotFound("Контактные данные профиля не найдены.")

		# Нормализация и расчет хешей
		email_hash = get_blind_index(normalize_email(fields["email"])) if "email" in fields else None
		phone_hash = get_blind_index(normalize_phone(fields["phone"])) if "phone" in fields else None

		# Проверка уникальности
		await uow.customers.check_contacts_unique(
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

		# Логирование события ДО коммита
		uow.add_event(LogEvent(
			user_id=user_id,
			action="update_contacts",
			service="customer_service",
			details=f"Обновлены контакты: {', '.join(fields.keys())}",
		))

		try:
			await uow.commit()
		except IntegrityError as exc:
			raise UpdateDataConflict("Конфликт уникальности контактов.") from exc

		await uow.customers.refresh(record)
		return schemas.ContactsResponse.model_validate(record)
