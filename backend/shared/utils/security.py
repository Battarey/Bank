"""Утилиты для обеспечения безопасности данных (шифрование и хеширование)."""

import hashlib
import os
from typing import Final

from cryptography.fernet import Fernet

# Ключ для симметричного шифрования (должен быть в base64, 32 байта)
ENCRYPTION_KEY: Final[str | None] = os.getenv("ENCRYPTION_KEY")

# Соль для слепого индекса (blind index), чтобы хеши не были предсказуемыми
BLIND_INDEX_SALT: Final[str] = os.getenv("BLIND_INDEX_SALT", "bank_default_salt_2024")


def encrypt_data(data: str) -> str:
	"""Шифрует строку с использованием Fernet (AES-128 в режиме CBC с HMAC).

	Args:
		data: Исходные данные в виде строки.

	Returns:
		Зашифрованные данные в формате Base64 (строка).

	Raises:
		ValueError: Если ENCRYPTION_KEY не задан.
	"""
	if not ENCRYPTION_KEY:
		raise ValueError("Переменная окружения ENCRYPTION_KEY не задана!")

	f = Fernet(ENCRYPTION_KEY.encode())
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
	if not ENCRYPTION_KEY:
		raise ValueError("Переменная окружения ENCRYPTION_KEY не задана!")

	f = Fernet(ENCRYPTION_KEY.encode())
	return f.decrypt(token.encode()).decode()


def get_blind_index(data: str) -> str:
	"""Создает детерминированный хеш (слепой индекс) для поиска по зашифрованным полям.

	Используется для обеспечения уникальности и возможности поиска (равенства),
	так как основное шифрование Fernet недетерминировано (разный IV при каждом вызове).

	Args:
		data: Исходные данные.

	Returns:
		Хеш в шестнадцатеричном формате.
	"""
	payload = f"{data}{BLIND_INDEX_SALT}"
	return hashlib.sha256(payload.encode()).hexdigest()


__all__ = [
	"decrypt_data",
	"encrypt_data",
	"get_blind_index",
]
