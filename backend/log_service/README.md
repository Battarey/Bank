# Сервис логирования

## Описание

RabbitMQ consumer (не HTTP-сервис), аналогично `notification_service`.
Слушает exchange `logs` (topic, binding `log.#`) и записывает каждое событие параллельно в два хранилища:

1. **PostgreSQL (postgres_history)** — таблица `user_actions`, полный аудит действий пользователей.
2. **ClickHouse** — таблица `business_events`, аналитика бизнес-событий (MergeTree, TTL 2 года, партиционирование по месяцам).

## Типы событий (Event Map)

Сервис обрабатывает события от всех бизнес-сервисов (auth, account, transaction, customer).

Подробная карта маршрутизации:
- **[Карта событий RabbitMQ](../../infra/docs/events.md)**

## Формат сообщения

```json
{
  "type": "transaction",
  "payload": {
    "user_id": "uuid",
    "action": "deposit",
    "service": "transaction_service",
    "entity_id": "uuid",
    "entity_type": "transaction",
    "amount": "1000.00",
    "currency": "RUB",
    "status": "success",
    "details": "Пополнение счёта 40817810...",
    "ip_address": null
  }
}
```

## Shared-модули

- `shared/history_core` — SQLAlchemy async engine + модель `UserAction`
- `shared/clickhouse_core` — clickhouse-connect async client + DDL `business_events`

## Зависимости

- `aio-pika` — подключение к RabbitMQ
- `sqlalchemy` + `asyncpg` — запись в PostgreSQL
- `clickhouse-connect` — запись в ClickHouse

## Переменные окружения

| Переменная           | Значение по умолчанию                                                                |
|----------------------|--------------------------------------------------------------------------------------|
| `RABBITMQ_URL`       | `amqp://guest:guest@rabbitmq:5672/`                                                  |
| `HISTORY_DATABASE_URL` | `postgresql+asyncpg://bank_history_user:...@postgres_history:5432/bank_history_db` |
| `CLICKHOUSE_HOST`    | `clickhouse`                                                                         |
| `CLICKHOUSE_PORT`    | `8123`                                                                               |
| `CLICKHOUSE_USER`    | `default`                                                                            | 
| `CLICKHOUSE_PASSWORD`| (из .env)                                                                            |
| `CLICKHOUSE_DB`      | `bank_logs`                                                                          |
