# notification_service/smtp

Низкоуровневый SMTP-транспорт для отправки email. Не знает о шаблонах — принимает готовые `subject` и `body`.

## Файловая архитектура

```
smtp/
├── __init__.py     # Реэкспорт: send_email
├── client.py       # SMTP-клиент (aiosmtplib)
└── README.md
```
  
## Публичный API

| Функция      | Сигнатура                                         | Описание                              |
|--------------|--------------------------------------------------|---------------------------------------|
| `send_email` | `async (to: str, subject: str, body: str) → None` | Отправить письмо с готовыми subject/body |

> Тема и тело письма формируются шаблонами (`notification_service/templates.py`), а не передаются напрямую.

## Конфигурация

Клиент читает переменные окружения при импорте модуля:

| Переменная      | Тип    | По умолчанию | Описание                                       |
|-----------------|--------|--------------|-------------------------------------------------|
| `SMTP_HOST`     | `str`  | `""`         | Хост SMTP-сервера                               |
| `SMTP_PORT`     | `int`  | `465`        | Порт (465 для TLS, 587 для STARTTLS)            |
| `SMTP_USER`     | `str`  | `""`         | Логин для аутентификации                        |
| `SMTP_PASSWORD` | `str`  | `""`         | Пароль / App Password                           |
| `SMTP_FROM`     | `str`  | `SMTP_USER`  | Адрес отправителя (поле `From`)                 |
| `SMTP_USE_TLS`  | `bool` | `true`       | Использовать TLS (`true`, `yes`, `1` → `True`)  |

> Если `SMTP_HOST` или `SMTP_USER` пусты — `send_email()` бросит `RuntimeError`.

## Зависимости

- `aiosmtplib>=3.0` — указана в `notification_service/requirements.txt`
