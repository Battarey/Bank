import os
from dataclasses import dataclass
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Настройка Jinja2
TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(
	loader=FileSystemLoader(TEMPLATES_DIR),
	autoescape=select_autoescape(["html", "xml"]),
)


@dataclass(frozen=True, slots=True)
class EmailTemplate:
	"""Определение email-шаблона."""

	name: str
	subject_template: str
	body_text_template: str
	html_template_name: str | None = None

	def render(self, variables: dict[str, Any]) -> tuple[str, str, str | None]:
		"""Подставить переменные в subject, body и html_body.

		Returns:
			(rendered_subject, rendered_body, rendered_html)
		"""
		subject = self.subject_template.format_map(variables)
		body_text = self.body_text_template.format_map(variables)
		
		html_body = None
		if self.html_template_name:
			template = env.get_template(self.html_template_name)
			html_body = template.render(subject=subject, name=self.name, **variables)

		return subject, body_text, html_body


# ── Шаблоны ────────────────────────────────────────────────────────────

VERIFICATION_CODE = EmailTemplate(
	name="verification_code",
	subject_template="Код подтверждения NEXUS",
	body_text_template="Ваш код подтверждения: {code}\nКод действителен 10 минут.",
	html_template_name="verification_code.html",
)

EMAIL_VERIFICATION = EmailTemplate(
	name="email_verification",
	subject_template="Подтверждение почты NEXUS",
	body_text_template="Ваш код для подтверждения email: {code}\nКод действителен 10 минут.",
	html_template_name="verification_code.html",
)

WELCOME = EmailTemplate(
	name="welcome",
	subject_template="Добро пожаловать в NEXUS!",
	body_text_template="Здравствуйте! Ваш аккаунт в NEXUS успешно создан.",
	html_template_name="welcome.html",
)

PIN_CHANGED = EmailTemplate(
	name="pin_changed",
	subject_template="NEXUS: PIN-код изменён",
	body_text_template="Ваш PIN-код был успешно изменён.",
	html_template_name="security_alert.html",
)

LOGIN_ALERT = EmailTemplate(
	name="login_alert",
	subject_template="NEXUS: Вход в аккаунт",
	body_text_template="Зафиксирован вход в ваш аккаунт NEXUS в {login_time}.",
	html_template_name="security_alert.html",
)

ACCOUNT_LOCKED = EmailTemplate(
	name="account_locked",
	subject_template="NEXUS: Аккаунт заблокирован",
	body_text_template="Ваш аккаунт был заблокирован из-за неверного ввода PIN-кода.",
	html_template_name="security_alert.html",
)

UNLOCK_CODE = EmailTemplate(
	name="unlock_code",
	subject_template="NEXUS: Код разблокировки",
	body_text_template="Ваш код разблокировки NEXUS: {code}",
	html_template_name="verification_code.html",
)

ACCOUNT_UNLOCKED = EmailTemplate(
	name="account_unlocked",
	subject_template="NEXUS: Аккаунт разблокирован",
	body_text_template="Ваш аккаунт NEXUS успешно разблокирован.",
	html_template_name="security_alert.html",
)

ACCOUNT_OPENED = EmailTemplate(
	name="account_opened",
	subject_template="NEXUS: Счёт открыт",
	body_text_template="Ваш {account_type} счёт в NEXUS успешно открыт.",
	html_template_name="account_status.html",
)

ACCOUNT_CLOSED = EmailTemplate(
	name="account_closed",
	subject_template="NEXUS: Счёт закрыт",
	body_text_template="Ваш счёт {account_number} в NEXUS успешно закрыт.",
	html_template_name="account_status.html",
)

TRANSACTION_DEPOSIT = EmailTemplate(
	name="transaction_deposit",
	subject_template="NEXUS: Пополнение счёта",
	body_text_template="Ваш счёт {account_number} пополнен на {amount} {currency}.",
	html_template_name="transaction.html",
)

TRANSACTION_WITHDRAWAL = EmailTemplate(
	name="transaction_withdrawal",
	subject_template="NEXUS: Списание со счёта",
	body_text_template="Со счёта {account_number} списано {amount} {currency}.",
	html_template_name="transaction.html",
)

TRANSACTION_TRANSFER = EmailTemplate(
	name="transaction_transfer",
	subject_template="NEXUS: Перевод выполнен",
	body_text_template="Перевод на сумму {amount} {currency} со счёта {from_account} на счёт {to_account} успешно выполнен.",
	html_template_name="transaction.html",
)

TRANSACTION_INCOMING = EmailTemplate(
	name="transaction_incoming",
	subject_template="NEXUS: Входящий перевод",
	body_text_template="На ваш счёт {account_number} поступил перевод {amount} {currency} со счёта {from_account}.",
	html_template_name="transaction.html",
)

ACCOUNT_FROZEN = EmailTemplate(
	name="account_frozen",
	subject_template="NEXUS: Счёт заморожен",
	body_text_template="Ваш счёт {account_number} был заморожен по причине: {reason}.",
	html_template_name="account_status.html",
)

ACCOUNT_UNFROZEN = EmailTemplate(
	name="account_unfrozen",
	subject_template="NEXUS: Счёт разморожен",
	body_text_template="Ваш счёт {account_number} успешно разморожен.",
	html_template_name="account_status.html",
)

ACCOUNT_SELF_BLOCKED = EmailTemplate(
	name="account_self_blocked",
	subject_template="NEXUS: Аккаунт заблокирован по запросу",
	body_text_template="Ваш аккаунт был заблокирован по вашему запросу.",
	html_template_name="security_alert.html",
)

SECURITY_FREEZE = EmailTemplate(
	name="security_freeze",
	subject_template="NEXUS: Заморозка безопасности",
	body_text_template="Счёт {account_number} заморожен системой безопасности: {rule}.",
	html_template_name="security_alert.html",
)

ACCOUNT_DELETED = EmailTemplate(
	name="account_deleted",
	subject_template="NEXUS: Аккаунт удалён",
	body_text_template="Ваш аккаунт в NEXUS был удалён по вашему запросу.",
	html_template_name="security_alert.html",
)

# ── Реестр ──────────────────────────────────────────────────────────────

TEMPLATES: dict[str, EmailTemplate] = {t.name: t for t in (
	VERIFICATION_CODE,
	EMAIL_VERIFICATION,
	WELCOME,
	PIN_CHANGED,
	LOGIN_ALERT,
	ACCOUNT_LOCKED,
	UNLOCK_CODE,
	ACCOUNT_UNLOCKED,
	ACCOUNT_OPENED,
	ACCOUNT_CLOSED,
	ACCOUNT_FROZEN,
	ACCOUNT_UNFROZEN,
	ACCOUNT_SELF_BLOCKED,
	SECURITY_FREEZE,
	ACCOUNT_DELETED,
	TRANSACTION_DEPOSIT,
	TRANSACTION_WITHDRAWAL,
	TRANSACTION_TRANSFER,
	TRANSACTION_INCOMING,
)}


def get_template(name: str) -> EmailTemplate:
	"""Получить шаблон по имени."""
	template = TEMPLATES.get(name)
	if template is None:
		raise ValueError(f"Шаблон '{name}' не найден.")
	return template


__all__ = [
	"EmailTemplate",
	"TEMPLATES",
	"get_template",
]
