"""MongoDB-журнал событий безопасности."""

from .client import init_mongo, close_mongo, save_event
