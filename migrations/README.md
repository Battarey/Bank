# Migrations

Сервис миграций базы данных. Управляет схемой PostgreSQL через Alembic и предоставляет скрипт полного сброса + накатки для dev-окружения.

## Файловая архитектура
```
migrations/
├── alembic/                          # Alembic-директория
│   ├── env.py                        # Конфигурация окружения (ALEMBIC_DATABASE_URL)
│   ├── script.py.mako                # Шаблон новой миграции
│   └── versions/                     # Файлы миграций
│       ├── postgre_core_init.py      # Инициализация схемы (7 таблиц)
│       ├── add_pin_hash.py           # Добавление pin_hash в users
│       ├── add_bank_accounts_client_id_idx.py  # Индекс bank_accounts.client_id
│       ├── add_transactions_account_id_idx.py  # Индекс transactions.account_id
│       └── add_freeze_columns.py     # Колонки frozen_by/frozen_at/freeze_reason в bank_accounts
├── postgre_core/                     # Документация таблиц (md-файл = таблица)
│   ├── users.md
│   ├── personal_data.md
│   ├── passport.md
│   ├── identifiers.md
│   ├── contacts.md
│   ├── bank_accounts.md
│   └── transactions.md
├── alembic.ini                       # Конфигурация Alembic
├── reset_and_upgrade.py              # Dev-скрипт: DROP → CREATE SCHEMA → upgrade head
├── Dockerfile                        # python:3.12-slim, CMD: alembic upgrade head
├── requirements.txt                  # alembic, SQLAlchemy, psycopg, python-dotenv
├── .env                              # ALEMBIC_DATABASE_URL и параметры PostgreSQL
└── README.md
```

## Конфигурация

| Переменная              | Обязательна | Описание                                              |
|-------------------------|-------------|-------------------------------------------------------|
| `ALEMBIC_DATABASE_URL`  | Да          | Sync URL PostgreSQL (`postgresql+psycopg://...`)      |
| `POSTGRES_CORE_DB`      | Да          | Имя базы данных                                       |
| `POSTGRES_CORE_USER`    | Да          | Пользователь PostgreSQL                               |
| `POSTGRES_CORE_PASSWORD`| Да          | Пароль PostgreSQL                                     |

> **Важно:** Alembic использует **синхронный** драйвер `psycopg`, а микросервисы — **асинхронный** `asyncpg`. Это разные URL.

## Docker

В `docker-compose.yaml` сервис `migrations` запускается с командой `python reset_and_upgrade.py` и зависит от `postgres_core` (condition: `service_healthy`). После выполнения контейнер останавливается (`restart: "no"`). Все микросервисы зависят от `migrations`.

```
postgres_core (healthy) → migrations → customer_service, auth_service, ...
```

## Хранилища данных

### PostgreSQL — `postgre_core`

Основная реляционная БД для учётных данных клиентов и банковских операций.

### Redis Sessions

Хранение сессионных токенов пользователей (TTL 30 мин). Инстанс: `redis_sessions` (Redis 7 Alpine).

### Redis Onboarding

Хранение JSON-черновиков шагов регистрации и onboarding-токенов (TTL 30 мин). Инстанс: `redis_onboarding` (Redis Stack).

### PostgreSQL History — `postgres_history`

Отдельный экземпляр PostgreSQL (порт 5433) для аудит-лога действий пользователей. Таблица `user_actions` создаётся автоматически через `HistoryBase.metadata.create_all` при запуске `log_service` (не через Alembic).

Модуль: `shared/history_core`.

### ClickHouse — `bank_logs`

Колоночная БД для аналитики бизнес-событий. Таблица `business_events` (MergeTree, партиционирование по месяцам, TTL 2 года). DDL создаётся автоматически при вызове `init_clickhouse()` в `log_service`.

Модуль: `shared/clickhouse_core`.

### MongoDB

Коллекция `email_log` в базе `bank_notifications_db`. Хранит журнал всех отправленных уведомлений (тип, получатель, тема, тело, статус, ошибка). TTL-индекс на `created_at` — автоматическое удаление через 90 дней. Инстанс: `mongodb` (Mongo 7).

## ER-диаграммы

### postgre_core

#### Простая версия
````mermaid
erDiagram
    USERS ||--|| PERSONAL_DATA : "client_id"
    USERS ||--|| PASSPORT : "client_id"
    USERS ||--|| IDENTIFIERS : "client_id"
    USERS ||--|| CONTACTS : "client_id"
    USERS ||--o{ BANK_ACCOUNTS : "client_id"
    BANK_ACCOUNTS ||--o{ TRANSACTIONS : "account_id"
    BANK_ACCOUNTS ||--o{ TRANSACTIONS : "related_account_id"
````

#### Подробная версия
````mermaid
erDiagram
    USERS {
        UUID id PK
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TEXT status
        BOOLEAN is_verified
        TEXT pin_hash
    }
    PERSONAL_DATA {
        UUID client_id FK
        VARCHAR last_name
        VARCHAR first_name
        VARCHAR middle_name
        DATE birth_date
        CHAR gender
    }
    PASSPORT {
        UUID client_id FK
        CHAR series
        CHAR number
        CHAR division_code
        TEXT issued_by
        DATE issued_at
        DATE expiration_date
        TEXT registration_address
    }
    IDENTIFIERS {
        UUID client_id FK
        CHAR inn
        CHAR snils
    }
    CONTACTS {
        UUID client_id FK
        VARCHAR email
        VARCHAR phone
    }
    BANK_ACCOUNTS {
        UUID id PK
        UUID client_id FK
        CHAR account_number
        TEXT type
        CHAR currency
        NUMERIC balance
        TEXT status
        TIMESTAMP opened_at
        TIMESTAMP closed_at
        TEXT frozen_by
        TIMESTAMP frozen_at
        TEXT freeze_reason
    }
    TRANSACTIONS {
        UUID id PK
        UUID account_id FK
        TEXT type
        NUMERIC amount
        TIMESTAMP created_at
        TEXT description
        UUID related_account_id FK
        TEXT direction
        TEXT status
        NUMERIC balance_before
        NUMERIC balance_after
        TEXT external_ref
    }

    USERS ||--|| PERSONAL_DATA : "client_id"
    USERS ||--|| PASSPORT : "client_id"
    USERS ||--|| IDENTIFIERS : "client_id"
    USERS ||--|| CONTACTS : "client_id"
    USERS ||--o{ BANK_ACCOUNTS : "client_id"
    BANK_ACCOUNTS ||--o{ TRANSACTIONS : "account_id"
    BANK_ACCOUNTS ||--o{ TRANSACTIONS : "related_account_id"
````

**Примечания**
- `||` — связь один-к-одному (`client_id` — уникальный PK для KYC-таблиц).
- `o{` — связь один-ко-многим: у клиента несколько счетов, у счёта много транзакций.
- `related_account_id` используется только для переводов (ссылка на второй счёт).
- Проверка диаграмм — https://mermaid.live

## Миграции

### Цепочка ревизий

```
(None) → postgre_core_init → add_pin_hash → add_bank_accounts_client_id_idx → add_transactions_account_id_idx → add_freeze_columns  ← HEAD
```

| Ревизия              | Описание                                                   |
|----------------------|-------------------------------------------------------------|
| `postgre_core_init`  | Создание 7 таблиц: users, personal_data, passport, identifiers, contacts, bank_accounts, transactions |
| `add_pin_hash`       | Добавление колонки `pin_hash` (Text, nullable) в `users`    |
| `add_bank_accounts_client_id_idx` | Индекс `ix_bank_accounts_client_id` на `bank_accounts.client_id` |
| `add_transactions_account_id_idx` | Индекс `ix_transactions_account_id` на `transactions.account_id` |
| `add_freeze_columns` | Добавление `frozen_by`, `frozen_at`, `freeze_reason` в `bank_accounts` |

### CHECK-ограничения

| Таблица         | Constraint                          | Допустимые значения                          |
|-----------------|-------------------------------------|----------------------------------------------|
| `users`         | `users_status_check`                | `pending`, `active`, `blocked`, `deleted`    |
| `personal_data` | `ck_personal_data_gender`           | `M`, `F`                                     |
| `bank_accounts` | `bank_accounts_type_check`          | `checking`, `savings`, `credit`, `deposit`   |
| `bank_accounts` | `bank_accounts_currency_check`      | `RUB`, `USD`, `EUR`                          |
| `bank_accounts` | `bank_accounts_status_check`        | `open`, `closed`, `frozen`                   |
| `transactions`  | `transactions_type_check`           | `deposit`, `withdrawal`, `transfer`          |
| `transactions`  | `transactions_direction_check`      | `incoming`, `outgoing`                       |
| `transactions`  | `transactions_status_check`         | `pending`, `posted`, `failed`                |

### `reset_and_upgrade.py`

Dev-скрипт для полного сброса базы:

1. Подключается через **синхронный** `psycopg` к PostgreSQL.
2. `DROP SCHEMA public CASCADE` → `CREATE SCHEMA public`.
3. Запускает `alembic upgrade head`.

> **Внимание:** уничтожает все данные. Используется только в dev-окружении.
