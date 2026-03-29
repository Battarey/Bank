"""Бизнес-логика онбординга — сохранение шагов, валидация, финализация."""

from datetime import UTC, datetime
from typing import Dict, Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models, schemas
from shared.redis_onboarding import drafts as onboarding_drafts
from shared.redis_onboarding.email_codes import clear_email_verification, is_email_verified
from shared.utils.normalize import digits_only, normalize_email, normalize_name, normalize_phone
from shared.utils.security import get_blind_index
from shared.utils.log_event import log_event
from shared.rabbitmq.constants import LOG_AUTH_KEY

from ..repository import CustomerRepository
from ..exceptions import (
	OnboardingConflict,
	OnboardingError,
)


async def start_onboarding(session: AsyncSession) -> UUID:
	"""Создаёт нового пользователя для процесса регистрации.

	Args:
		session: Асинхронная сессия базы данных.

	Returns:
		UUID: Идентификатор созданного пользователя.

	Raises:
		OnboardingError: Если не удалось создать пользователя после нескольких попыток.
	"""
	repo = CustomerRepository(session)
	
	for _ in range(5):
		candidate_id = uuid4()
		if await repo.get(candidate_id):
			continue
			
		user = models.User(
			id=candidate_id,
			created_at=datetime.now(UTC),
			updated_at=datetime.now(UTC),
			status="pending",
			is_verified=False,
		)
		await repo.add(user)
		try:
			await repo.commit()
		except Exception:
			await repo.rollback()
			raise
		return candidate_id

	raise OnboardingError("Не удалось инициализировать процесс регистрации.")


async def store_personal_data(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PersonalDataPayload,
) -> schemas.PersonalDataResponse:
	"""Сохраняет черновик первого шага (ФИО, дата рождения) в Redis.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		payload: Данные профиля.

	Returns:
		PersonalDataResponse: Сохранённые данные.

	Raises:
		OnboardingNotFound: Если сессия регистрации не найдена.
	"""
	repo = CustomerRepository(session)
	await repo.get_active_user(user_id)  # Проверка существования

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
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PassportPayload,
) -> schemas.PassportResponse:
	"""Сохраняет черновик паспортных данных с проверкой уникальности.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		payload: Данные паспорта.

	Returns:
		PassportResponse: Сохранённые данные.

	Raises:
		OnboardingConflict: Если паспорт уже используется.
		OnboardingNotFound: Если пользователь не найден.
	"""
	repo = CustomerRepository(session)
	await repo.get_active_user(user_id)

	normalized = payload.model_copy(
		update={
			"issued_by": payload.issued_by.strip(),
			"registration_address": payload.registration_address.strip(),
		},
	)
	
	# Проверка уникальности по хешу
	p_hash = get_blind_index(f"{normalized.series}{normalized.number}")
	await repo.check_passport_unique(p_hash, exclude_client_id=user_id)
	
	await onboarding_drafts.save_draft(user_id, "passport", normalized.model_dump(mode="json"))
	
	return schemas.PassportResponse(
		client_id=user_id,
		**normalized.model_dump(),
	)


async def store_identifiers(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
) -> schemas.IdentifiersResponse:
	"""Сохраняет ИНН и СНИЛС в черновик.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		payload: Идентификаторы.

	Returns:
		IdentifiersResponse: Подтверждение сохранения.
	"""
	repo = CustomerRepository(session)
	await repo.get_active_user(user_id)

	normalized = payload.model_copy(
		update={
			"inn": digits_only(payload.inn),
			"snils": digits_only(payload.snils),
		},
	)
	
	await repo.check_identifiers_unique(
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
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.ContactsPayload,
) -> schemas.ContactsResponse:
	"""Сохраняет контакты (email, phone) в черновик.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		payload: Контактные данные.

	Returns:
		ContactsResponse: Сохранённые контакты.
	"""
	repo = CustomerRepository(session)
	await repo.get_active_user(user_id)

	normalized = payload.model_copy(
		update={
			"email": normalize_email(payload.email),
			"phone": normalize_phone(payload.phone),
		},
	)
	
	await repo.check_contacts_unique(
		email_hash=get_blind_index(normalized.email),
		phone_hash=get_blind_index(normalized.phone),
		exclude_client_id=user_id
	)
	
	await onboarding_drafts.save_draft(user_id, "contacts", normalized.model_dump(mode="json"))
	
	return schemas.ContactsResponse(
		client_id=user_id,
		**normalized.model_dump(),
	)


async def persist_onboarding_data(session: AsyncSession, user_id: UUID) -> None:
	"""Переносит все накопленные черновики из Redis в Postgres.

	Завершает процесс регистрации: переводит статус пользователя в 'active',
	очищает черновики и отправляет событие в лог.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.

	Raises:
		OnboardingError: Если не все шаги заполнены или email не верифицирован.
		OnboardingConflict: При коллизии уникальных данных в БД.
	"""
	repo = CustomerRepository(session)
	
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
		await repo.add_profile_part(models.PersonalData(client_id=user_id, **p_data.model_dump()))
		
		# Passport
		passport = drafts["passport"]
		await repo.add_profile_part(models.Passport(
			client_id=user_id,
			passport_hash=get_blind_index(f"{passport.series}{passport.number}"),
			**passport.model_dump()
		))
		
		# Identifiers
		ids = drafts["identifiers"]
		await repo.add_profile_part(models.Identifier(client_id=user_id, **ids.model_dump()))
		
		# Contacts
		contacts = drafts["contacts"]
		await repo.add_profile_part(models.Contact(
			client_id=user_id,
			email_hash=get_blind_index(contacts.email),
			phone_hash=get_blind_index(contacts.phone),
			**contacts.model_dump()
		))
		
		# Акцивация пользователя
		user = await repo.get_active_user(user_id)
		user.status = "active"
		user.is_verified = True
		user.updated_at = datetime.now(UTC)
		
		await repo.commit()
		
	except IntegrityError as exc:
		await repo.rollback()
		raise OnboardingConflict("Данные конфликтуют с существующим клиентом.") from exc
	except Exception:
		await repo.rollback()
		raise

	# 3. Очистка и логирование
	await onboarding_drafts.clear_all(user_id)
	await clear_email_verification(user_id)
	
	await log_event(
		routing_key=LOG_AUTH_KEY,
		event_type="auth",
		payload={
			"user_id": str(user_id),
			"action": "registration",
			"service": "customer_service",
			"status": "success",
			"details": "Регистрация завершена (онбординг финализирован)",
		}
	)
