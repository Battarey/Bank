# Шаблоны

Реестр email-шаблонов. Определяет все допустимые типы писем — произвольные письма отправить нельзя.

## Файловая архитектура

```
templates/
├── __init__.py       # Реэкспорт публичного API
├── templates.py      # EmailTemplate, шаблоны, реестр TEMPLATES
└── README.md
```

## Публичный API

| Экспорт            | Тип                         | Описание                                        |
|---------------------|------------------------------|----------------------------------------------------|
| `get_template(name)` | `(str) → EmailTemplate`     | Получить шаблон по имени (или `ValueError`)     |
| `TEMPLATES`          | `dict[str, EmailTemplate]`   | Реестр всех шаблонов                              |
| `VERIFICATION_CODE`  | `EmailTemplate`              | Код подтверждения email                          |
| `WELCOME`            | `EmailTemplate`              | Приветственное письмо                               |
| `PIN_CHANGED`        | `EmailTemplate`              | Уведомление о смене PIN                            |
| `LOGIN_ALERT`        | `EmailTemplate`              | Уведомление о входе в аккаунт                      |
| `ACCOUNT_LOCKED`     | `EmailTemplate`              | Уведомление о блокировке аккаунта              |
| `UNLOCK_CODE`        | `EmailTemplate`              | Код разблокировки аккаунта                       |
| `ACCOUNT_UNLOCKED`   | `EmailTemplate`              | Уведомление о разблокировке                       |
| `ACCOUNT_OPENED`     | `EmailTemplate`              | Уведомление об открытии счёта                     |
| `ACCOUNT_CLOSED`     | `EmailTemplate`              | Уведомление о закрытии счёта                      |
| `TRANSACTION_DEPOSIT` | `EmailTemplate`              | Уведомление о пополнении счёта                    |
| `TRANSACTION_WITHDRAWAL` | `EmailTemplate`           | Уведомление о списании со счёта                   |
| `TRANSACTION_TRANSFER` | `EmailTemplate`             | Уведомление об исходящем переводе                 |
| `TRANSACTION_INCOMING` | `EmailTemplate`             | Уведомление о входящем переводе                   |
| `ACCOUNT_FROZEN`       | `EmailTemplate`             | Уведомление о заморозке счёта                     |
| `ACCOUNT_UNFROZEN`     | `EmailTemplate`             | Уведомление о разморозке счёта                    |
| `ACCOUNT_SELF_BLOCKED` | `EmailTemplate`             | Уведомление о самоблокировке аккаунта              |
| `SECURITY_FREEZE`      | `EmailTemplate`             | Уведомление о заморозке по проверке безопасности   |
| `EmailTemplate`      | `dataclass`                  | Класс шаблона (`name`, `subject`, `body`, `render()`) |

## Шаблоны

| Имя                  | Тема письма                   | Переменные       |
|----------------------|----------------------------|-------------------|
| `verification_code`  | Код подтверждения email    | `{code}`          |
| `welcome`            | Добро пожаловать в Bank App! | —                 |
| `pin_changed`        | PIN-код изменён            | —                 |
| `login_alert`        | Вход в аккаунт             | `{login_time}`    |
| `account_locked`     | Аккаунт заблокирован        | —                 |
| `unlock_code`        | Код разблокировки аккаунта| `{code}`          |
| `account_unlocked`   | Аккаунт разблокирован      | —                 |
| `account_opened`     | Счёт открыт                | `{account_type}`, `{currency}`, `{account_number}` |
| `account_closed`     | Счёт закрыт                | `{account_number}` |
| `transaction_deposit` | Пополнение счёта           | `{account_number}`, `{amount}`, `{currency}`, `{balance_after}` |
| `transaction_withdrawal` | Списание со счёта       | `{account_number}`, `{amount}`, `{currency}`, `{balance_after}` |
| `transaction_transfer` | Перевод выполнен          | `{from_account}`, `{to_account}`, `{amount}`, `{currency}`, `{balance_after}` |
| `transaction_incoming` | Входящий перевод          | `{account_number}`, `{from_account}`, `{amount}`, `{currency}`, `{balance_after}` |
| `account_frozen`     | Счёт заморожен              | `{account_number}`, `{frozen_by}`, `{reason}` |
| `account_unfrozen`   | Счёт разморожен             | `{account_number}` |
| `account_self_blocked` | Аккаунт заблокирован по запросу | — |
| `security_freeze`    | Счёт заморожен по проверке безопасности | `{account_number}`, `{rule}`, `{details}` |

## EmailTemplate

```python
@dataclass(frozen=True, slots=True)
class EmailTemplate:
    name: str        # Имя шаблона (совпадает с type в сообщении RabbitMQ)
    subject: str     # Тема письма (может содержать {placeholders})
    body: str        # Тело письма (может содержать {placeholders})

    def render(self, variables: dict) -> tuple[str, str]:
        """Returns (rendered_subject, rendered_body)"""
```

## Как добавить новый шаблон

1. Создать экземпляр `EmailTemplate` в `templates.py`:

```python
PASSWORD_RESET = EmailTemplate(
    name="password_reset",
    subject="Сброс пароля",
    body="Ссылка для сброса: {reset_link}\n\nСсылка действительна 15 минут.",
)
```

2. Добавить в кортеж реестра:

```python
TEMPLATES: dict[str, EmailTemplate] = {t.name: t for t in (
    ...,
    PASSWORD_RESET,
)}
```

3. Публиковать из любого сервиса:

```python
await publish(NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY, {
    "type": "password_reset",
    "payload": {"to": "user@example.com", "variables": {"reset_link": "https://..."}},
})
```
