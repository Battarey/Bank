"""SQLAlchemy-модели, переиспользуемые микросервисами."""

from .base import Base
from .contact import Contact
from .identifier import Identifier
from .passport import Passport
from .personal_data import PersonalData
from .user import User

__all__ = [
	"Base",
	"Contact",
	"Identifier",
	"Passport",
	"PersonalData",
	"User",
]
