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
| `EmailTemplate`      | `dataclass`                  | Класс шаблона (`name`, `subject`, `body`, `render()`) |

## Шаблоны

| Имя                  | Тема письма                   | Переменные       |
|----------------------|----------------------------|-------------------|
| `verification_code`  | Код подтверждения email    | `{code}`          |
| `welcome`            | Добро пожаловать в Bank App! | —                 |
| `pin_changed`        | PIN-код изменён            | —                 |
| `login_alert`        | Вход в аккаунт             | `{login_time}`    |

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
