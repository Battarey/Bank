# Security Service

Внутренний микросервис AML / антифрод-проверок операций по банковским счетам.

## Назначение

Сервис проверяет каждую исходящую транзакцию (`withdrawal`, `transfer`) по набору AML-правил.
При срабатывании хотя бы одного правила операция **блокируется**, счёт **замораживается** автоматически
(`frozen_by = "system"`), событие логируется в MongoDB, а владельцу отправляется email.

## Архитектура

```
transaction_service ──POST /check──▶ security_service
                                          │
                                          ├──▶ PostgreSQL  (чтение истории транзакций)
                                          └──▶ MongoDB     (журнал security_events)
```

Сервис **не вызывается** напрямую из Gateway — только через `transaction_service`
(fail-open: при недоступности security_service транзакция проходит).

## AML-правила

Сервис проверяет каждую операцию по 6 ключевым правилам (крупные транзакции, дробление, аномальная активность). Пороги срабатывания настраиваются через переменные окружения.

Подробное описание правил:
- **[Стандарты AML-проверок](../../infra/docs/api_standards.md#правила-антифрода-aml)**

## Эндпоинты

| Метод | Путь     | Описание                          | Защита             |
|-------|----------|-----------------------------------|--------------------|
| POST  | `/check` | Проверить pending-транзакцию      | `X-Internal-Key`   |
| GET   | `/health`| Healthcheck                       | `X-Internal-Key`   |

### POST /check

**Request body:**
```json
{
  "account_id": "uuid",
  "tx_type": "withdrawal | transfer",
  "amount": 500000.00,
  "currency": "RUB"
}
```

**Response:**
```json
{
  "allowed": false,
  "violations": [
    {
      "rule": "large_single_tx",
      "threshold": "600000",
      "actual": "500000",
      "details": {}
    }
  ]
}
```

## MongoDB

- База: `bank_security_db`
- Коллекция: `security_events`
- TTL-индекс: 365 дней (`created_at`)

## Переменные окружения

| Переменная                 | Обязательная | Описание                                    |
|----------------------------|:------------:|---------------------------------------------|
| `DATABASE_URL`             | ✓           | URL PostgreSQL (чтение транзакций)          |
| `INTERNAL_API_KEY`         | ✓           | Ключ для inter-service авторизации          |
| `RABBITMQ_URL`             | ✓           | URL брокера для email-уведомлений           |
| `MONGO_URL`                | ✓           | URL MongoDB для журнала событий             |
| `LARGE_TX_THRESHOLD`       |              | Порог крупной операции (default: 600000)    |
| `DAILY_AMOUNT_LIMIT`       |              | Лимит суммы за 24 ч (default: 1000000)      |
| `DAILY_TX_COUNT`           |              | Лимит операций за 24 ч (default: 20)        |
| `RAPID_FIRE_COUNT`         |              | Лимит rapid-fire (default: 5)               |
| `RAPID_FIRE_WINDOW_MIN`    |              | Окно rapid-fire в минутах (default: 3)      |
| `STRUCTURING_RATIO`        |              | Коэффициент дробления (default: 0.9)        |
| `STRUCTURING_MIN_HITS`     |              | Минимум попаданий structuring (default: 3)  |
| `ROUND_AMOUNT_FLOOR`       |              | Нижний порог круглых сумм (default: 100000) |
| `ROUND_AMOUNT_STEP`        |              | Шаг кратности (default: 10000)              |
| `ROUND_AMOUNT_MIN_HITS`    |              | Минимум круглых сумм (default: 3)           |

## Зависимости

- PostgreSQL (через `shared/database_core`)
- MongoDB (через `motor`)
- RabbitMQ (через `shared/rabbitmq`)
