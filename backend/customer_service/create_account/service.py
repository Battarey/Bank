"""Бизнес-логика онбординга — сохранение шагов, валидация, финализация."""

from datetime import UTC, datetime
from typing import Dict, Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from shared.events.base import LogEvent, NotificationEvent
from shared.redis_onboarding import drafts as onboarding_drafts
from shared.redis_onboarding.email_codes import clear_email_verification, is_email_verified
from shared.utils.normalize import digits_only, normalize_email, normalize_name, normalize_phone
from shared.utils.security import get_blind_index

from ..uow import CustomerUnitOfWork
from ..exceptions import (
	OnboardingConflict,
	OnboardingError,
)


async def start_onboarding(uow: CustomerUnitOfWork) -> UUID:
	"""Создаёт нового пользователя для процесса регистрации.

	Args:
		uow: Unit of Work для управления транзакциями.

	Returns:
		UUID: Идентификатор созданного пользователя.

	Raises:
		OnboardingError: Если не удалось создать пользователя после нескольких попыток.
	"""
	async with uow:
		for _ in range(5):
			candidate_id = uuid4()
			if await uow.customers.get(candidate_id):
				continue
				
			user = models.User(
				id=candidate_id,
				created_at=datetime.now(UTC),
				updated_at=datetime.now(UTC),
				status="pending",
				is_verified=False,
			)
			await uow.customers.add(user)
			await uow.commit()
			return candidate_id

	raise OnboardingError("Не удалось инициализировать процесс регистрации.")


async def store_personal_data(
	uow: CustomerUnitOfWork,
	user_id: UUID,
	payload: schemas.PersonalDataPayload,
) -> schemas.PersonalDataResponse:
	"""Сохраняет черновик первого шага (ФИО) в Redis.

	Args:
		uow: Unit of Work для проверки существования пользователя.
		user_id: ID пользователя.
		payload: Данные профиля (ФИО).

	Returns:
		schemas.PersonalDataResponse: Сохранённые нормализованные данные.

	Raises:
		OnboardingNotFound: Если сессия регистрации не найдена.
	"""
	async with uow:
		await uow.customers.get_active_user(user_id)  # Проверка существования

	normalized = payload.model_copy(
		update={
			"last_name": normalize_name(payload.last_name),
			"first_name": normalize_name(payload.first_name),
			"middle_name": normalize_name(payload.middle_name),
		},
	)
	
	await onboarding_drafts.save_draft(user_id, "personal_data", normalized.model_dump(mode="json"))
	
	return schemas.PersonalDataResponse(
		client_id=user_id,
		**normalized.model_dump(),
	)


async def store_passport_data(
	uow: CustomerUnitOfWork,
	user_id: UUID,
	payload: schemas.PassportPayload,
) -> schemas.PassportResponse:
	"""Сохраняет черновик паспортных данных в Redis с проверкой уникальности.

	Args:
		uow: Unit of Work для проверки уникальности паспорта.
		user_id: ID пользователя.
		payload: Данные паспорта.

	Returns:
		schemas.PassportResponse: Сохранённые данные.

	Raises:
		OnboardingConflict: Если паспорт уже используется другим пользователем.
		OnboardingNotFound: Если пользователь не найден.
	"""
	async with uow:
		await uow.customers.get_active_user(user_id)

	normalized = payload.model_copy(
		update={
			"issued_by": payload.issued_by.strip(),
			"registration_address": payload.registration_address.strip(),
		},
	)
	
	# Проверка уникальности по хешу
	p_hash = get_blind_index(f"{normalized.series}{normalized.number}")
	await uow.customers.check_passport_unique(p_hash, exclude_client_id=user_id)
	
	await onboarding_drafts.save_draft(user_id, "passport", normalized.model_dump(mode="json"))
	
	return schemas.PassportResponse(
		client_id=user_id,
		**normalized.model_dump(),
	)


async def store_identifiers(
	uow: CustomerUnitOfWork,
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
) -> schemas.IdentifiersResponse:
	"""Сохраняет ИНН и СНИЛС в черновик (Redis).

	Args:
		uow: Unit of Work для проверки уникальности идентификаторов.
		user_id: ID пользователя.
		payload: Идентификаторы (ИНН, СНИЛС).

	Returns:
		schemas.IdentifiersResponse: Подтверждение сохранения.

	Raises:
		OnboardingConflict: Если ИНН или СНИЛС уже заняты.
	"""
	async with uow:
		await uow.customers.get_active_user(user_id)

	normalized = payload.model_copy(
		update={
			"inn": digits_only(payload.inn),
			"snils": digits_only(payload.snils),
		},
	)
	
	await uow.customers.check_identifiers_unique(
		inn_hash=normalized.inn, 
		snils_hash=normalized.snils, 
		exclude_client_id=user_id
	)
	
	await onboarding_drafts.save_draft(user_id, "identifiers", normalized.model_dump(mode="json"))
	
	return schemas.IdentifiersResponse(
		client_id=user_id,
		**normalized.model_dump(),
	)


async def store_contacts(
	uow: CustomerUnitOfWork,
	user_id: UUID,
	payload: schemas.ContactsPayload,
) -> schemas.ContactsResponse:
	"""Сохраняет контактные данные (Email, телефон) в черновик.

	Args:
		uow: Unit of Work для проверки уникальности контактов.
		user_id: ID пользователя.
		payload: Контактные данные.

	Returns:
		schemas.ContactsResponse: Сохранённые контакты.

	Raises:
		OnboardingConflict: Если Email или телефон уже используются.
	"""
	async with uow:
		await uow.customers.get_active_user(user_id)

	normalized = payload.model_copy(
		update={
			"email": normalize_email(payload.email),
			"phone": normalize_phone(payload.phone),
		},
	)
	
	await uow.customers.check_contacts_unique(
		email_hash=get_blind_index(normalized.email),
		phone_hash=get_blind_index(normalized.phone),
		exclude_client_id=user_id
	)
	
	await onboarding_drafts.save_draft(user_id, "contacts", normalized.model_dump(mode="json"))
	
	return schemas.ContactsResponse(
		client_id=user_id,
		**normalized.model_dump(),
	)


async def persist_onboarding_data(uow: CustomerUnitOfWork, user_id: UUID) -> None:
	"""Переносит все накопленные черновики из Redis в Postgres, завершая регистрацию.

	1. Сбор и валидация всех черновиков из Redis.
	2. Проверка верификации Email.
	3. Сохранение данных во все связанные таблицы профиля.
	4. Активация пользователя и логирование.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID пользователя.

	Raises:
		OnboardingError: Если не все шаги заполнены или email не верифицирован.
		OnboardingConflict: При коллизии уникальных данных в БД.
	"""
	async with uow:
		# 1. Сбор и валидация черновиков
		drafts: Dict[str, Any] = {}
		missing = []
		steps = [
			("personal_data", schemas.PersonalDataPayload),
			("passport", schemas.PassportPayload),
			("identifiers", schemas.IdentifiersPayload),
			("contacts", schemas.ContactsPayload),
		]
		
		for step_name, schema in steps:
			draft = await onboarding_drafts.load_draft(user_id, step_name)
			if not draft or not draft.get("payload"):
				missing.append(step_name)
			else:
				drafts[step_name] = schema.model_validate(draft["payload"])
				
		if missing:
			raise OnboardingError(f"Не все шаги онбординга завершены: {', '.join(missing)}")

		if not await is_email_verified(user_id):
			raise OnboardingError("Email не подтверждён. Финализация невозможна.")

		# 2. Сохранение в БД
		try:
			# Personal Data
			p_data = drafts["personal_data"]
			await uow.customers.add_profile_part(models.PersonalData(client_id=user_id, **p_data.model_dump()))
			
			# Passport
			passport = drafts["passport"]
			await uow.customers.add_profile_part(models.Passport(
				client_id=user_id,
				passport_hash=get_blind_index(f"{passport.series}{passport.number}"),
				**passport.model_dump()
			))
			
			# Identifiers
			ids = drafts["identifiers"]
			await uow.customers.add_profile_part(models.Identifier(client_id=user_id, **ids.model_dump()))
			
			# Contacts
			contacts = drafts["contacts"]
			await uow.customers.add_profile_part(models.Contact(
				client_id=user_id,
				email_hash=get_blind_index(contacts.email),
				phone_hash=get_blind_index(contacts.phone),
				**contacts.model_dump()
			))
			
			# Активация пользователя
			user = await uow.customers.get_active_user(user_id)
			user.status = "active"
			user.is_verified = True
			user.updated_at = datetime.now(UTC)
			
			# Регистрация событий ДО коммита
			uow.add_event(LogEvent(
				user_id=user_id,
				action="registration",
				service="customer_service",
				details="Регистрация завершена (онбординг финализирован)",
			))
			
			uow.add_event(NotificationEvent(
				type="registration_success",
				to=contacts.email,
				variables={
					"user_id": str(user_id),
					"first_name": drafts["personal_data"].first_name,
				},
			))

			await uow.commit()
			
		except IntegrityError as exc:
			raise OnboardingConflict("Данные конфликтуют с существующим клиентом.") from exc

		# 3. Очистка черновиков (внешние по отношению к БД ресурсы)
		await onboarding_drafts.clear_all(user_id)
		await clear_email_verification(user_id)
