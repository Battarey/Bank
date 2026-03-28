# Справочник переменных окружения (.env)

Данный документ объединяет все переменные, необходимые для работы Monorepo.

## 1. Общая инфраструктура

| Переменная          | Назначение                                     |
|:--------------------|:-----------------------------------------------|
| `POSTGRES_USER`     | Владелец всех баз данных                       |
| `POSTGRES_PASSWORD` | Пароль пользователя                            |
| `INTERNAL_API_KEY`  | Глобальный секрет для межсервисной авторизации |
| `RABBITMQ_URL`      | Формат: `amqp://user:pass@rabbitmq:5672/`      |

## 2. Базы данных и кэши

| Сервис        | Переменная                | Описание                        |
|:--------------|:--------------------------|:--------------------------------|
| `core_db`     | `DATABASE_URL`            | Основная БД клиентов (asyncpg)  |
| `history_db`  | `HISTORY_DATABASE_URL`    | БД аудит-лога (asyncpg)         |
| `onboarding`  | `REDIS_ONBOARDING_URL`    | Redis Stack для черновиков      |
| `sessions`    | `REDIS_SESSIONS_URL`      | Redis для сессий (TTL)          |
| `analytis`    | `CLICKHOUSE_HOST / PORT`  | ClickHouse для бизнес-событий   |
| `security`    | `MONGO_URL`               | MongoDB для журнала безопасности|

## 3. Внешние ключи API

| Сервис             | Переменная              | Источник             |
|:-------------------|:------------------------|:---------------------|
| `metal_service`    | `METALS_DEV_API_KEY`    | metals.dev           |
| `currency_service` | `EXCHANGE_RATE_API_KEY` | exchangerate-api.com |
| `notification`     | `SMTP_PASSWORD`         | App Password (Gmail) |

## 4. Настройки безопасности (AML)

| Сервис     | Переменная             | Значение (Default) |
|:-----------|:-----------------------|:-------------------|
| `security` | `LARGE_TX_THRESHOLD`   | 600 000            |
| `security` | `DAILY_AMOUNT_LIMIT`   | 1 000 000          |
| `security` | `DAILY_TX_COUNT`       | 20                 |
