"""Кастомные типы данных SQLAlchemy."""

from typing import Any

from sqlalchemy import Text, TypeDecorator

from shared.utils.security import decrypt_data, encrypt_data


class EncryptedString(TypeDecorator):
	"""Автоматически шифрует строку при сохранении и расшифровывает при чтении.

	Использует Fernet для симметричного шифрования.
	Поскольку Fernet недетерминирован (разные IV), поиск по этим полям невозможен.
	Для поиска используйте Blind Index.
	"""

	impl = Text
	cache_ok = True

	def process_bind_param(self, value: Any, _dialect: Any) -> str | None:
		if value is not None:
			return encrypt_data(str(value))
		return value

	def process_result_value(self, value: Any, _dialect: Any) -> str | None:
		if value is not None:
			return decrypt_data(str(value))
		return value


__all__ = ["EncryptedString"]
