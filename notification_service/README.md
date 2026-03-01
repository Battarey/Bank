# notification_service

Воркер-сервис для отправки уведомлений. Потребляет сообщения из RabbitMQ и отправляет email через SMTP.

> **Не является HTTP-сервисом** — не экспонирует порты, работает как фоновый consumer.

## Файловая архитектура

```
notification_service/
├── __init__.py
├── Dockerfile
├── main.py             # Точка входа — RabbitMQ consumer
├── requirements.txt
├── .env                # SMTP + RABBITMQ + MONGO конфиг
├── smtp/               # SMTP-клиент (транспорт)
├── store/              # MongoDB-журнал отправленных уведомлений
├── templates/           # Реестр email-шаблонов
└── README.md
```

## Как работает

```
customer_service ──(publish)──► RabbitMQ ──(consume)──► notification_service ──(SMTP)──► Gmail
                                                              │
                                                              └──(save)──► MongoDB (email_log)
```

1. Любой сервис публикует JSON-сообщение в exchange `notifications` с routing key `email.send`
2. `notification_service` слушает очередь `email_queue` (binding: `email.#`)
3. Поле `type` определяет **шаблон** — произвольные письма не отправляются
4. Переменные из `payload.variables` подставляются в шаблон и отправляются через SMTP
5. Результат (успех/ошибка) сохраняется в MongoDB-коллекцию `email_log`

## Журнал уведомлений (`store/`)

Каждое отправленное (или неудавшееся) письмо сохраняется в MongoDB как документ:

```json
{
  "type": "account_opened",
  "to": "user@example.com",
  "subject": "Счёт открыт",
  "body": "Здравствуйте! ...",
  "variables": { "account_type": "Расчётный", "currency": "RUB", "account_number": "40817810..." },
  "status": "sent",
  "error": null,
  "created_at": "2026-03-01T12:00:00Z"
}
```

- **TTL:** документы автоматически удаляются через 90 дней (индекс на `created_at`)
- **Статус:** `sent` — успешно, `failed` — ошибка (поле `error` содержит описание)

## Шаблоны (`templates/`)

Все допустимые типы писем определены в реестре `TEMPLATES`. Произвольные письма не отправляются — подробнее в `templates/README.md`.

## Формат сообщений

### Общий формат

```json
{
  "type": "<имя_шаблона>",
  "payload": {
    "to": "user@example.com",
    "variables": { "key": "value" }
  }
}
```

### Пример: `verification_code`

```json
{
  "type": "verification_code",
  "payload": {
    "to": "user@example.com",
    "variables": { "code": "482910" }
  }
}
```

### Пример: `welcome` (без переменных)

```json
{
  "type": "welcome",
  "payload": {
    "to": "user@example.com",
    "variables": {}
  }
}
```

> Если `type` не найден в реестре шаблонов — сообщение логируется как предупреждение и игнорируется.

## Переменные окружения

| Переменная      | Описание                         | Пример                                    |
|-----------------|----------------------------------|-------------------------------------------|
| `RABBITMQ_URL`  | URL подключения к RabbitMQ       | `amqp://guest:guest@rabbitmq:5672/`       |
| `MONGO_URL`     | URL подключения к MongoDB        | `mongodb://user:pass@mongodb:27017/db?authSource=admin` |
| `SMTP_HOST`     | SMTP сервер                      | `smtp.gmail.com`                          |
| `SMTP_PORT`     | Порт SMTP                        | `465`                                     |
| `SMTP_USER`     | Логин SMTP                       | `user@gmail.com`                          |
| `SMTP_PASSWORD` | Пароль / App Password            | `xxxx xxxx xxxx xxxx`                     |
| `SMTP_FROM`     | Адрес отправителя (по умолч. = SMTP_USER) | `user@gmail.com`               |
| `SMTP_USE_TLS`  | Использовать TLS (`true`/`false`) | `true`                                   |

## Docker

- **Сети**: `frontend`, `backend`, `data`
- **Зависимости**: `rabbitmq`, `mongodb`
- **CMD**: `python -m notification_service.main`

## Расширение

Для добавления нового типа письма:

1. Создать `EmailTemplate` в `templates/templates.py` и добавить в реестр `TEMPLATES`
2. Публиковать сообщение с соответствующим `type` из любого сервиса

Подробнее — в `templates/README.md`.
