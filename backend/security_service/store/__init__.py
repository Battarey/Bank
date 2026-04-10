"""MongoDB-журнал событий безопасности."""

from .client import close_mongo as close_mongo
from .client import init_mongo as init_mongo
from .client import save_event as save_event
