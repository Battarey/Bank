"""MongoDB-журнал отправленных уведомлений."""

from .client import close_mongo, get_mongo, init_mongo, save_notification

__all__ = [
	"close_mongo",
	"get_mongo",
	"init_mongo",
	"save_notification",
]
