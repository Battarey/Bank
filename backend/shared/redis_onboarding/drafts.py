"""Помощники для хранения черновиков онбординга в Redis."""

from datetime import timedelta
from typing import Any, Literal, Sequence, TypedDict
from uuid import UUID
from .client import get_client

DEFAULT_DRAFT_TTL = timedelta(hours=24)

StepName = Literal["personal_data", "passport", "identifiers", "contacts"]
ALL_STEPS: Sequence[StepName] = (
	"personal_data",
	"passport",
	"identifiers",
	"contacts",
)


class DraftRecord(TypedDict, total=False):
	payload: dict[str, Any]
	status: Literal["pending", "validated"]
	updated_at: str  # Временная метка в формате ISO


def _key(user_id: UUID, step: StepName) -> str:
	return f"onboarding:{user_id}:{step}"


async def save_draft(
	user_id: UUID,
	step: StepName,
	payload: dict[str, Any],
	status: DraftRecord["status"] = "pending",
	ttl: timedelta = DEFAULT_DRAFT_TTL,
) -> None:
	"""Сохранить или перезаписать данные черновика для указанного шага онбординга."""

	client = get_client()
	record: DraftRecord = {
		"payload": payload,
		"status": status,
	}
	await client.json().set(_key(user_id, step), "$", record)
	await client.expire(_key(user_id, step), int(ttl.total_seconds()))


async def load_draft(user_id: UUID, step: StepName) -> DraftRecord | None:
	"""Получить данные черновика, если они существуют."""

	client = get_client()
	return await client.json().get(_key(user_id, step))


async def clear_draft(user_id: UUID, step: StepName) -> None:
	"""Удалить черновик конкретного шага."""

	client = get_client()
	await client.delete(_key(user_id, step))


async def clear_all(user_id: UUID) -> None:
	"""Удалить все черновики онбординга для пользователя."""

	client = get_client()
	await client.delete(*[_key(user_id, step) for step in ALL_STEPS])


__all__ = [
	"ALL_STEPS",
	"DEFAULT_DRAFT_TTL",
	"DraftRecord",
	"StepName",
	"clear_all",
	"clear_draft",
	"load_draft",
	"save_draft",
]
