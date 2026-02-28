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

# ── Реестр ──────────────────────────────────────────────────────────────

TEMPLATES: dict[str, EmailTemplate] = {t.name: t for t in (
	VERIFICATION_CODE,
	WELCOME,
	PIN_CHANGED,
	LOGIN_ALERT,
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
	"EmailTemplate",
	"LOGIN_ALERT",
	"PIN_CHANGED",
	"TEMPLATES",
	"VERIFICATION_CODE",
	"WELCOME",
	"get_template",
]
