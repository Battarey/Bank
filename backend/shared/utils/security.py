"""Утилиты для обеспечения безопасности данных (шифрование и хеширование)."""

import hashlib
import logging
from shared.bootstrap import get_container

from cryptography.fernet import Fernet


def encrypt_data(data: str) -> str:
	"""Шифрует строку с использованием Fernet (AES-128 в режиме CBC с HMAC).

	Ключ извлекается из глобального контейнера настроек.

	Args:
		data: Исходные данные в виде строки.

	Returns:
		Зашифрованные данные в формате Base64 (строка).

	Raises:
		ValueError: Если ENCRYPTION_KEY не задан.
	"""
	settings = get_container().settings
	key = settings.ENCRYPTION_KEY

	if not key:
		raise ValueError("Настройка ENCRYPTION_KEY не задана!")

	f = Fernet(key.encode())
	return f.encrypt(data.encode()).decode()


def decrypt_data(token: str) -> str:
	"""Расшифровывает строку, зашифрованную через Fernet.

	Args:
		token: Зашифрованные данные (Base64).

	Returns:
		Исходная строка.

	Raises:
		ValueError: Если ENCRYPTION_KEY не задан.
	"""
	settings = get_container().settings
	key = settings.ENCRYPTION_KEY

	if not key:
		raise ValueError("Настройка ENCRYPTION_KEY не задана!")

	f = Fernet(key.encode())
	return f.decrypt(token.encode()).decode()


def get_blind_index(data: str) -> str:
	"""Создает детерминированный хеш (слепой индекс) для поиска по зашифрованным полям.

	Args:
		data: Исходные данные.

	Returns:
		Хеш в шестнадцатеричном формате.
	"""
	settings = get_container().settings
	salt = settings.BLIND_INDEX_SALT

	payload = f"{data}{salt}"
	return hashlib.sha256(payload.encode()).hexdigest()


__all__ = [
	"decrypt_data",
	"encrypt_data",
	"get_blind_index",
]
