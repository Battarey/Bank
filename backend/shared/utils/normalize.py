"""Утилиты нормализации данных.

Переиспользуемые функции для приведения пользовательского ввода
к единому формату перед сохранением или сравнением.
"""


def normalize_name(value: str | None) -> str | None:
	"""Стандартизирует ФИО: strip + UPPER."""
	if value is None:
		return None
	return value.strip().upper()


def normalize_email(value: str) -> str:
	"""Приводит email к нижнему регистру."""
	return value.lower()


def normalize_phone(value: str) -> str:
	"""Удаляет пробелы в телефонном номере."""
	return value.replace(" ", "")


def digits_only(value: str) -> str:
	"""Оставляет только цифры (ИНН, СНИЛС и т.д.)."""
	return "".join(ch for ch in value if ch.isdigit())


__all__ = [
	"digits_only",
	"normalize_email",
	"normalize_name",
	"normalize_phone",
]
