"""Шаблоны email-уведомлений.

Каждый шаблон — dataclass с subject_template и body_template.
Переменные подставляются через str.format_map().
Реестр TEMPLATES связывает строковое имя шаблона с его определением.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmailTemplate:
	"""Определение email-шаблона."""

	name: str
	subject: str
	body: str

	def render(self, variables: dict[str, str]) -> tuple[str, str]:
		"""Подставить переменные в subject и body.

		Returns:
			(rendered_subject, rendered_body)

		Raises:
			KeyError: если в variables нет обязательной переменной.
		"""
		return (
			self.subject.format_map(variables),
			self.body.format_map(variables),
		)


# ── Шаблоны ────────────────────────────────────────────────────────────

VERIFICATION_CODE = EmailTemplate(
	name="verification_code",
	subject="Код подтверждения email",
	body=(
		"Ваш код подтверждения: {code}\n\n"
		"Код действителен 10 минут.\n"
		"Если вы не запрашивали код, проигнорируйте это письмо."
	),
)

WELCOME = EmailTemplate(
	name="welcome",
	subject="Добро пожаловать в Bank App!",
	body=(
		"Здравствуйте!\n\n"
		"Ваш аккаунт успешно создан.\n"
		"Если у вас возникнут вопросы, свяжитесь с нашей службой поддержки.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

PIN_CHANGED = EmailTemplate(
	name="pin_changed",
	subject="PIN-код изменён",
	body=(
		"Здравствуйте!\n\n"
		"Ваш PIN-код был успешно изменён.\n"
		"Если вы не совершали это действие, немедленно свяжитесь с поддержкой.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

LOGIN_ALERT = EmailTemplate(
	name="login_alert",
	subject="Вход в аккаунт",
	body=(
		"Здравствуйте!\n\n"
		"Зафиксирован вход в ваш аккаунт.\n"
		"Время: {login_time}\n\n"
		"Если это были не вы, немедленно смените PIN-код и свяжитесь с поддержкой.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

ACCOUNT_LOCKED = EmailTemplate(
	name="account_locked",
	subject="Аккаунт заблокирован",
	body=(
		"Здравствуйте!\n\n"
		"Ваш аккаунт был заблокирован из-за многократного неверного ввода PIN-кода "
		"(15 неудачных попыток).\n\n"
		"Для разблокировки отправьте запрос через /auth/request-unlock и введите "
		"6-значный код, который придёт на этот email.\n\n"
		"Если это были не вы, немедленно свяжитесь с поддержкой.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

UNLOCK_CODE = EmailTemplate(
	name="unlock_code",
	subject="Код разблокировки аккаунта",
	body=(
		"Ваш код разблокировки: {code}\n\n"
		"Код действителен 10 минут.\n"
		"Если вы не запрашивали разблокировку, немедленно свяжитесь с поддержкой."
	),
)

ACCOUNT_UNLOCKED = EmailTemplate(
	name="account_unlocked",
	subject="Аккаунт разблокирован",
	body=(
		"Здравствуйте!\n\n"
		"Ваш аккаунт успешно разблокирован.\n"
		"Теперь вы можете войти по PIN-коду.\n\n"
		"Если вы не запрашивали разблокировку, немедленно свяжитесь с поддержкой.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

ACCOUNT_OPENED = EmailTemplate(
	name="account_opened",
	subject="Счёт открыт",
	body=(
		"Здравствуйте!\n\n"
		"Ваш {account_type} счёт успешно открыт.\n"
		"Валюта: {currency}\n"
		"Номер счёта: {account_number}\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

ACCOUNT_CLOSED = EmailTemplate(
	name="account_closed",
	subject="Счёт закрыт",
	body=(
		"Здравствуйте!\n\n"
		"Ваш счёт {account_number} успешно закрыт.\n"
		"Если вы не совершали это действие, немедленно свяжитесь с поддержкой.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

TRANSACTION_DEPOSIT = EmailTemplate(
	name="transaction_deposit",
	subject="Пополнение счёта",
	body=(
		"Здравствуйте!\n\n"
		"Ваш счёт {account_number} пополнен на {amount} {currency}.\n"
		"Текущий баланс: {balance_after} {currency}.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

TRANSACTION_WITHDRAWAL = EmailTemplate(
	name="transaction_withdrawal",
	subject="Списание со счёта",
	body=(
		"Здравствуйте!\n\n"
		"Со счёта {account_number} списано {amount} {currency}.\n"
		"Текущий баланс: {balance_after} {currency}.\n\n"
		"Если вы не совершали это действие, немедленно свяжитесь с поддержкой.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

TRANSACTION_TRANSFER = EmailTemplate(
	name="transaction_transfer",
	subject="Перевод выполнен",
	body=(
		"Здравствуйте!\n\n"
		"Перевод {amount} {currency} выполнен.\n"
		"Со счёта: {from_account}\n"
		"На счёт: {to_account}\n"
		"Баланс счёта-отправителя: {balance_after} {currency}.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

TRANSACTION_INCOMING = EmailTemplate(
	name="transaction_incoming",
	subject="Входящий перевод",
	body=(
		"Здравствуйте!\n\n"
		"На ваш счёт {account_number} поступил перевод {amount} {currency} "
		"со счёта {from_account}.\n"
		"Текущий баланс: {balance_after} {currency}.\n\n"
		"С уважением,\n"
		"Команда Bank App"
	),
)

# ── Реестр ──────────────────────────────────────────────────────────────

TEMPLATES: dict[str, EmailTemplate] = {t.name: t for t in (
	VERIFICATION_CODE,
	WELCOME,
	PIN_CHANGED,
	LOGIN_ALERT,
	ACCOUNT_LOCKED,
	UNLOCK_CODE,
	ACCOUNT_UNLOCKED,
	ACCOUNT_OPENED,
	ACCOUNT_CLOSED,
	TRANSACTION_DEPOSIT,
	TRANSACTION_WITHDRAWAL,
	TRANSACTION_TRANSFER,
	TRANSACTION_INCOMING,
)}


def get_template(name: str) -> EmailTemplate:
	"""Получить шаблон по имени.

	Raises:
		ValueError: если шаблон не найден.
	"""
	template = TEMPLATES.get(name)
	if template is None:
		raise ValueError(
			f"Шаблон '{name}' не найден. "
			f"Доступные: {', '.join(TEMPLATES.keys())}"
		)
	return template


__all__ = [
	"ACCOUNT_LOCKED",
	"ACCOUNT_UNLOCKED",
	"EmailTemplate",
	"LOGIN_ALERT",
	"PIN_CHANGED",
	"TEMPLATES",
	"UNLOCK_CODE",
	"VERIFICATION_CODE",
	"WELCOME",
	"get_template",
]
