"""Подключение к PostgreSQL History — база аудит-лога действий пользователя."""

from .models import HistoryBase, UserAction


def __getattr__(name):
	from . import db

	if name in ("HistorySessionLocal", "get_history_session", "history_engine"):
		return getattr(db, name)
	raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
	"HistoryBase",
	"HistorySessionLocal",
	"UserAction",
	"get_history_session",
	"history_engine",
]
