"""Rate-limiter для PIN-аутентификации.

Механика:
- Счётчик неудачных попыток ввода PIN (`total_failures`) хранится в Redis.
- Каждые 5 неудач устанавливается кулдаун на 5 минут (`cooldown`).
- После 15 суммарных неудач аккаунт блокируется (status → "blocked").
- Успешный вход сбрасывает все счётчики.
"""

from datetime import timedelta
from uuid import UUID

from .client import get_client

MAX_FAILURES_PER_BLOCK: int = 5
MAX_BLOCKS: int = 3
TOTAL_MAX_FAILURES: int = MAX_FAILURES_PER_BLOCK * MAX_BLOCKS  # 15
COOLDOWN_TTL: timedelta = timedelta(minutes=5)


def _total_key(phone: str) -> str:
	return f"rate:pin:{phone}:total"


def _cooldown_key(phone: str) -> str:
	return f"rate:pin:{phone}:cooldown"


# ── Проверка ────────────────────────────────────────────────────────────

async def check_cooldown(phone: str) -> int | None:
	"""Проверить, действует ли кулдаун.

	Returns:
		Оставшееся время кулдауна в секундах, или None если кулдауна нет.
	"""
	client = get_client()
	ttl = await client.ttl(_cooldown_key(phone))
	if ttl > 0:
		return ttl
	return None


async def get_total_failures(phone: str) -> int:
	"""Получить текущее количество неудачных попыток."""
	client = get_client()
	val = await client.get(_total_key(phone))
	return int(val) if val else 0


# ── Запись неудачи ──────────────────────────────────────────────────────

async def record_failure(phone: str) -> tuple[int, bool, bool]:
	"""Зафиксировать неудачную попытку ввода PIN.

	Returns:
		(total_failures, cooldown_started, should_lock)
		- total_failures: общее число неудач после инкремента
		- cooldown_started: True если начался новый 5-минутный кулдаун
		- should_lock: True если достигнут лимит и аккаунт нужно заблокировать
	"""
	client = get_client()

	total = await client.incr(_total_key(phone))

	should_lock = total >= TOTAL_MAX_FAILURES
	cooldown_started = False

	if should_lock:
		# Достигнут предел — очищаем ключи, блокировка будет на уровне БД
		await client.delete(_total_key(phone), _cooldown_key(phone))
	elif total % MAX_FAILURES_PER_BLOCK == 0:
		# Каждые 5 неудач — кулдаун 5 минут
		await client.set(
			_cooldown_key(phone),
			"1",
			ex=int(COOLDOWN_TTL.total_seconds()),
		)
		cooldown_started = True

	return total, cooldown_started, should_lock


# ── Сброс ───────────────────────────────────────────────────────────────

async def reset(phone: str) -> None:
	"""Сбросить все счётчики (при успешном входе или разблокировке)."""
	client = get_client()
	await client.delete(_total_key(phone), _cooldown_key(phone))


__all__ = [
	"COOLDOWN_TTL",
	"MAX_BLOCKS",
	"MAX_FAILURES_PER_BLOCK",
	"TOTAL_MAX_FAILURES",
	"check_cooldown",
	"get_total_failures",
	"record_failure",
	"reset",
]
