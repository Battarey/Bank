"""Бизнес-логика обновления данных пользователя."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models, schemas


class UpdateDataError(Exception):
	"""Общая ошибка при обновлении данных."""


class UpdateDataNotFound(UpdateDataError):
	"""Запись не найдена для обновления."""


class UpdateDataConflict(UpdateDataError):
	"""Конфликт уникальности при обновлении."""


class UpdateDataEmpty(UpdateDataError):
	"""Пустой запрос — ни одно поле не передано."""


def _normalize_name(value: str | None) -> str | None:
	if value is None:
		return None
	return value.strip().upper()


def _normalize_email(value: str) -> str:
	return value.lower()


def _normalize_phone(value: str) -> str:
	return value.replace(" ", "")


async def _get_active_user(session: AsyncSession, user_id: UUID) -> models.User:
	"""Возвращает пользователя, если он в активном статусе."""
	user = await session.get(models.User, user_id)
	if user is None:
		raise UpdateDataNotFound(f"Пользователь {user_id} не найден.")
	if user.status != "active":
		raise UpdateDataError(
			f"Обновление данных доступно только для активных пользователей (текущий статус: {user.status})."
		)
	return user


# ── Персональные данные (ФИО) ──────────────────────────────────────────


async def update_personal_data(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PersonalDataUpdate,
) -> schemas.PersonalDataResponse:
	"""Обновляет ФИО пользователя. birth_date и gender неизменяемы."""

	fields = payload.model_dump(exclude_unset=True)
	if not fields:
		raise UpdateDataEmpty("Необходимо передать хотя бы одно поле для обновления.")

	user = await _get_active_user(session, user_id)
	record = await session.get(models.PersonalData, user_id)
	if record is None:
		raise UpdateDataNotFound("Персональные данные пользователя не найдены.")

	# Нормализация
	if "last_name" in fields:
		fields["last_name"] = _normalize_name(fields["last_name"])
	if "first_name" in fields:
		fields["first_name"] = _normalize_name(fields["first_name"])
	if "middle_name" in fields:
		fields["middle_name"] = _normalize_name(fields["middle_name"])

	for attr, value in fields.items():
		setattr(record, attr, value)

	user.updated_at = datetime.now(UTC)

	try:
		await session.commit()
	except Exception:
		await session.rollback()
		raise

	await session.refresh(record)
	return schemas.PersonalDataResponse.model_validate(record)


# ── Паспорт (замена целиком) ───────────────────────────────────────────


async def replace_passport(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.PassportPayload,
) -> schemas.PassportResponse:
	"""Полная замена паспортных данных (перевыпуск паспорта)."""

	user = await _get_active_user(session, user_id)
	record = await session.get(models.Passport, user_id)
	if record is None:
		raise UpdateDataNotFound("Паспортные данные пользователя не найдены.")

	# Нормализация
	normalized = payload.model_copy(
		update={
			"issued_by": payload.issued_by.strip(),
			"registration_address": payload.registration_address.strip(),
		},
	)

	# Проверка уникальности серии/номера
	duplicate = await session.scalar(
		select(models.Passport).where(
			models.Passport.series == normalized.series,
			models.Passport.number == normalized.number,
		)
	)
	if duplicate and duplicate.client_id != user_id:
		raise UpdateDataConflict("Паспорт с такой серией/номером уже привязан к другому клиенту.")

	for attr, value in normalized.model_dump().items():
		setattr(record, attr, value)

	user.updated_at = datetime.now(UTC)

	try:
		await session.commit()
	except IntegrityError as exc:
		await session.rollback()
		raise UpdateDataConflict("Конфликт данных паспорта.") from exc
	except Exception:
		await session.rollback()
		raise

	await session.refresh(record)
	return schemas.PassportResponse.model_validate(record)


# ── Контакты (partial) ────────────────────────────────────────────────


async def update_contacts(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.ContactsUpdate,
) -> schemas.ContactsResponse:
	"""Частичное обновление email и/или phone."""

	fields = payload.model_dump(exclude_unset=True)
	if not fields:
		raise UpdateDataEmpty("Необходимо передать хотя бы одно поле для обновления.")

	user = await _get_active_user(session, user_id)
	record = await session.get(models.Contact, user_id)
	if record is None:
		raise UpdateDataNotFound("Контактные данные пользователя не найдены.")

	# Нормализация
	if "email" in fields:
		fields["email"] = _normalize_email(fields["email"])
	if "phone" in fields:
		fields["phone"] = _normalize_phone(fields["phone"])

	# Проверка уникальности
	conditions = []
	if "email" in fields:
		conditions.append(models.Contact.email == fields["email"])
	if "phone" in fields:
		conditions.append(models.Contact.phone == fields["phone"])

	if conditions:
		duplicate = await session.scalar(
			select(models.Contact).where(or_(*conditions))
		)
		if duplicate and duplicate.client_id != user_id:
			raise UpdateDataConflict("Email или телефон уже используется другим клиентом.")

	for attr, value in fields.items():
		setattr(record, attr, value)

	user.updated_at = datetime.now(UTC)

	try:
		await session.commit()
	except IntegrityError as exc:
		await session.rollback()
		raise UpdateDataConflict("Email или телефон уже используется другим клиентом.") from exc
	except Exception:
		await session.rollback()
		raise

	await session.refresh(record)
	return schemas.ContactsResponse.model_validate(record)


__all__ = [
	"UpdateDataConflict",
	"UpdateDataEmpty",
	"UpdateDataError",
	"UpdateDataNotFound",
	"replace_passport",
	"update_contacts",
	"update_personal_data",
]
