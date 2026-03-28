"""Базовый класс для всех ORM-моделей."""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
	"""Базовый класс для всех ORM-моделей сервиса."""

__all__ = ["Base"]
