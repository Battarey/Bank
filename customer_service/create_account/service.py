from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Awaitable, Callable, Dict
from uuid import UUID, uuid4
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from shared import models, schemas
from shared.redis_onboarding import drafts as onboarding_drafts


class AccountDataError(Exception):
	"""Общее исключение при работе с данными онбординга."""


class AccountDataConflict(AccountDataError):
	"""Возникает при конфликте вводимых данных с уже существующими."""


EnsureNoRecordFn = Callable[[AsyncSession, UUID], Awaitable[None]]
EnsureUniqueFn = Callable[[AsyncSession, UUID, BaseModel], Awaitable[None]]
NormalizeFn = Callable[[BaseModel], BaseModel]
ModelFactoryFn = Callable[[UUID, BaseModel], object]


@dataclass(frozen=True)
class StepDefinition:
	"""Описывает, как обрабатывать конкретный шаг онбординга."""

	step: onboarding_drafts.StepName
	payload_model: type[BaseModel]
	response_model: type[BaseModel]
	conflict_message: str
	ensure_no_record: EnsureNoRecordFn
	normalize: NormalizeFn
	ensure_unique: EnsureUniqueFn | None
	model_factory: ModelFactoryFn


async def _get_or_create_user(session: AsyncSession, user_id: UUID) -> models.User:
	"""Возвращает пользователя либо создаёт новую запись для онбординга."""

	user = await session.get(models.User, user_id)
	if user:
		return user

	now = datetime.now(UTC)
	user = models.User(
		id=user_id,
		created_at=now,
		updated_at=now,
		status="pending",
		is_verified=False,
	)
	session.add(user)
	return user


def _normalize_name(value: str | None) -> str | None:
	"""Стандартизирует ФИО для сравнения (upper + trim)."""

	if value is None:
		return None
	return value.strip().upper()


def _normalize_email(value: str) -> str:
	"""Приводит email к нижнему регистру."""
	return value.lower()



def _normalize_phone(value: str) -> str:
	"""Удаляет пробелы в телефонном номере."""
	return value.replace(" ", "")


def _digits_only(value: str) -> str:
	"""Оставляет только цифры (ИНН/СНИЛС)."""
	return "".join(ch for ch in value if ch.isdigit())


def _normalize_personal_payload(payload: schemas.PersonalDataPayload) -> schemas.PersonalDataPayload:
	"""Возвращает копию с нормализованными текстовыми полями персонального шага."""

	return payload.model_copy(
		update={
			"last_name": _normalize_name(payload.last_name),
			"first_name": _normalize_name(payload.first_name),
			"middle_name": _normalize_name(payload.middle_name),
		},
	)


def _normalize_passport_payload(payload: schemas.PassportPayload) -> schemas.PassportPayload:
	"""Очищает строковые поля паспорта от пробелов по краям."""
	return payload.model_copy(
		update={
			"issued_by": payload.issued_by.strip(),
			"registration_address": payload.registration_address.strip(),
		},
	)


def _normalize_identifiers_payload(payload: schemas.IdentifiersPayload) -> schemas.IdentifiersPayload:
	"""Удаляет нецифровые символы из ИНН/СНИЛС."""
	return payload.model_copy(
		update={
			"inn": _digits_only(payload.inn),
			"snils": _digits_only(payload.snils),
		},
	)


def _normalize_contacts_payload(payload: schemas.ContactsPayload) -> schemas.ContactsPayload:
	"""Нормализует email и телефон для поиска дублей."""
	return payload.model_copy(
		update={
			"email": _normalize_email(payload.email),
			"phone": _normalize_phone(payload.phone),
		},
	)


async def _ensure_no_personal_data_record(session: AsyncSession, user_id: UUID) -> None:
	"""Предотвращает повторный ввод персональных данных."""
	if await session.get(models.PersonalData, user_id):
		raise AccountDataConflict("Personal data already captured for this user.")


async def _ensure_no_passport_record(session: AsyncSession, user_id: UUID) -> None:
	"""Проверяет, что паспорт не сохранён."""
	if await session.get(models.Passport, user_id):
		raise AccountDataConflict("Passport data already captured for this user.")


async def _ensure_no_identifiers_record(session: AsyncSession, user_id: UUID) -> None:
	"""Следит, чтобы ИНН/СНИЛС не были записаны ранее."""
	if await session.get(models.Identifier, user_id):
		raise AccountDataConflict("Identifiers already captured for this user.")


async def _ensure_no_contacts_record(session: AsyncSession, user_id: UUID) -> None:
	"""Не допускает повторного сохранения контактов."""
	if await session.get(models.Contact, user_id):
		raise AccountDataConflict("Contact data already captured for this user.")


async def _ensure_no_draft(user_id: UUID, step: onboarding_drafts.StepName, message: str) -> None:
	"""Блокирует дублирующие черновики в Redis."""
	if await onboarding_drafts.load_draft(user_id, step):
		raise AccountDataConflict(message)


async def _ensure_passport_unique(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PassportPayload,
) -> None:
	"""Проверяет уникальность серии/номера паспорта."""
	duplicate = await session.scalar(
		select(models.Passport).where(
			models.Passport.series == payload.series,
			models.Passport.number == payload.number,
		)
	)
	if duplicate and duplicate.client_id != user_id:
		raise AccountDataConflict("Passport is already linked to another client.")


async def _ensure_identifiers_unique(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
) -> None:
	"""Проверяет уникальность ИНН/СНИЛС."""
	duplicate = await session.scalar(
		select(models.Identifier).where(
			or_(
				models.Identifier.inn == payload.inn,
				models.Identifier.snils == payload.snils,
			)
		)
	)
	if duplicate and duplicate.client_id != user_id:
		raise AccountDataConflict("Provided INN or SNILS already belongs to another client.")


async def _ensure_contacts_unique(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.ContactsPayload,
) -> None:
	"""Проверяет, что email/phone ещё не заняты."""
	duplicate = await session.scalar(
		select(models.Contact).where(
			or_(
				models.Contact.email == payload.email,
				models.Contact.phone == payload.phone,
			)
		)
	)
	if duplicate and duplicate.client_id != user_id:
		raise AccountDataConflict("Provided email or phone already belongs to another client.")


def _personal_model_factory(user_id: UUID, payload: schemas.PersonalDataPayload) -> models.PersonalData:
	"""Создаёт ORM-модель персональных данных."""
	return models.PersonalData(client_id=user_id, **payload.model_dump())


def _passport_model_factory(user_id: UUID, payload: schemas.PassportPayload) -> models.Passport:
	"""Создаёт ORM-модель паспорта."""
	return models.Passport(client_id=user_id, **payload.model_dump())


def _identifiers_model_factory(user_id: UUID, payload: schemas.IdentifiersPayload) -> models.Identifier:
	"""Создаёт ORM-модель идентификаторов."""
	return models.Identifier(client_id=user_id, **payload.model_dump())


def _contacts_model_factory(user_id: UUID, payload: schemas.ContactsPayload) -> models.Contact:
	"""Создаёт ORM-модель контактов."""
	return models.Contact(client_id=user_id, **payload.model_dump())


STEP_DEFINITIONS: Dict[onboarding_drafts.StepName, StepDefinition] = {
	"personal_data": StepDefinition(
		step="personal_data",
		payload_model=schemas.PersonalDataPayload,
		response_model=schemas.PersonalDataResponse,
		conflict_message="Personal data already captured for this user.",
		ensure_no_record=_ensure_no_personal_data_record,
		normalize=_normalize_personal_payload,
		ensure_unique=None,
		model_factory=_personal_model_factory,
	),
	"passport": StepDefinition(
		step="passport",
		payload_model=schemas.PassportPayload,
		response_model=schemas.PassportResponse,
		conflict_message="Passport data already captured for this user.",
		ensure_no_record=_ensure_no_passport_record,
		normalize=_normalize_passport_payload,
		ensure_unique=_ensure_passport_unique,
		model_factory=_passport_model_factory,
	),
	"identifiers": StepDefinition(
		step="identifiers",
		payload_model=schemas.IdentifiersPayload,
		response_model=schemas.IdentifiersResponse,
		conflict_message="Identifiers already captured for this user.",
		ensure_no_record=_ensure_no_identifiers_record,
		normalize=_normalize_identifiers_payload,
		ensure_unique=_ensure_identifiers_unique,
		model_factory=_identifiers_model_factory,
	),
	"contacts": StepDefinition(
		step="contacts",
		payload_model=schemas.ContactsPayload,
		response_model=schemas.ContactsResponse,
		conflict_message="Contact data already captured for this user.",
		ensure_no_record=_ensure_no_contacts_record,
		normalize=_normalize_contacts_payload,
		ensure_unique=_ensure_contacts_unique,
		model_factory=_contacts_model_factory,
	),
}

STEP_SEQUENCE = tuple(STEP_DEFINITIONS[step] for step in onboarding_drafts.ALL_STEPS)


async def start_onboarding(session: AsyncSession) -> UUID:
	"""Создаёт нового пользователя для онбординга и возвращает его идентификатор."""

	for _ in range(5):
		candidate_id = uuid4()
		if await session.get(models.User, candidate_id):
			continue  # крайне маловероятный коллизия UUID
			
		await _get_or_create_user(session, candidate_id)
		try:
			await session.commit()
		except Exception:
			await session.rollback()
			raise
		return candidate_id

	raise AccountDataError("Не удалось создать нового пользователя для онбординга.")


async def _ensure_user_exists(session: AsyncSession, user_id: UUID) -> None:
	"""Проверяет, что пользователь с данным ID создан через start_onboarding."""
	user = await session.get(models.User, user_id)
	if user is None:
		raise AccountDataError(f"Пользователь {user_id} не найден. Сначала вызовите /users/start.")


async def _store_step(
	session: AsyncSession,
	user_id: UUID,
	payload: BaseModel,
	definition: StepDefinition,
) -> BaseModel:
	"""Проводит общий пайплайн шага: проверки → нормализация → сохранение черновика."""

	await _ensure_user_exists(session, user_id)
	await definition.ensure_no_record(session, user_id)
	await _ensure_no_draft(user_id, definition.step, definition.conflict_message)
	normalized_payload = definition.normalize(payload)
	if definition.ensure_unique:
		await definition.ensure_unique(session, user_id, normalized_payload)
	await onboarding_drafts.save_draft(
		user_id,
		definition.step,
		normalized_payload.model_dump(mode="json"),
	)
	return definition.response_model(
		client_id=user_id,
		**normalized_payload.model_dump(),
	)


async def _persist_step(
	session: AsyncSession,
	user_id: UUID,
	payload: BaseModel,
	definition: StepDefinition,
) -> None:
	"""Переносит подготовленный payload шага в PostgreSQL."""

	await definition.ensure_no_record(session, user_id)
	normalized_payload = definition.normalize(payload)
	if definition.ensure_unique:
		await definition.ensure_unique(session, user_id, normalized_payload)
	user = await _get_or_create_user(session, user_id)
	session.add(definition.model_factory(user_id, normalized_payload))
	user.updated_at = datetime.now(UTC)


async def store_personal_data(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PersonalDataPayload,
) -> schemas.PersonalDataResponse:
	"""Пишет черновик шага персональных данных в Redis."""
	definition = STEP_DEFINITIONS["personal_data"]
	return await _store_step(session, user_id, payload, definition)


async def store_passport_data(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PassportPayload,
) -> schemas.PassportResponse:
	"""Сохраняет черновик паспортного шага."""
	definition = STEP_DEFINITIONS["passport"]
	return await _store_step(session, user_id, payload, definition)


async def store_identifiers(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
) -> schemas.IdentifiersResponse:
	"""Сохраняет черновик ИНН/СНИЛС."""
	definition = STEP_DEFINITIONS["identifiers"]
	return await _store_step(session, user_id, payload, definition)


async def store_contacts(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.ContactsPayload,
) -> schemas.ContactsResponse:
	"""Сохраняет черновик контактного шага."""
	definition = STEP_DEFINITIONS["contacts"]
	return await _store_step(session, user_id, payload, definition)


async def persist_onboarding_data(session: AsyncSession, user_id: UUID) -> None:
	"""Переносит все черновики из Redis в PostgreSQL и очищает их."""

	draft_payloads: Dict[onboarding_drafts.StepName, BaseModel] = {}
	missing_steps: list[str] = []
	for definition in STEP_SEQUENCE:
		record = await onboarding_drafts.load_draft(user_id, definition.step)
		if record is None or not record.get("payload"):
			missing_steps.append(definition.step)
		else:
			draft_payloads[definition.step] = definition.payload_model.model_validate(record["payload"])

	if missing_steps:
		raise AccountDataError(
			f"Не заполнены или истекли черновики шагов: {', '.join(missing_steps)}. "
			"Заполните их заново перед финализацией."
		)

	try:
		for definition in STEP_SEQUENCE:
			await _persist_step(session, user_id, draft_payloads[definition.step], definition)

		user = await session.get(models.User, user_id)
		if user:
			user.status = "active"
			user.is_verified = True
			user.updated_at = datetime.now(UTC)

		await session.commit()
	except IntegrityError as exc:
		await session.rollback()
		raise AccountDataConflict(
			"Данные конфликтуют с уже существующими записями (дубликат уникального поля)."
		) from exc
	except Exception:
		await session.rollback()
		raise
	else:
		await onboarding_drafts.clear_all(user_id)


__all__ = [
	"AccountDataConflict",
	"AccountDataError",
	"start_onboarding",
	"persist_onboarding_data",
	"store_contacts",
	"store_identifiers",
	"store_passport_data",
	"store_personal_data",
]
