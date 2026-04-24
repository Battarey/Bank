# Infrastructure

Папка для конфигураций окружения, развертывания и мониторинга всего Monorepo.

## Документация архитектуры
Здесь собраны все ключевые стандарты и правила проекта:
- **[API & Архитектурные стандарты](./docs/api_standards.md)**: Номера счетов, AML-политики, правила блокировок.
- **[Схема базы данных](./README.md#схема-базы-данных)**: ER-диаграммы и детальное описание таблиц PostgreSQL.
- **[Карта событий (RabbitMQ)](./docs/events.md)**: Кто шлет логи и уведомления.
- **[Внешние интеграции](./docs/external_integrations.md)**: Настройка Metals.Dev, ExchangeRate и SMTP.
- **[Справочник переменных окружения (.env)](./env/README.md)**: Мастер-таблица всех ключей и настроек.

## Содержимое папки:
- `docs/`: Детальные спецификации БД и архитектурные стандарты.
- `env/`: Справочник переменных окружения и шаблоны `.env.example`.
- `audit/`: Конфигурации и скрипты для автоматизированного аудита кода (Ruff, Vulture, Deptry).
- `docker/`: (В разработке) Общие Docker-файлы или специфичные конфиги.

## Сети Docker

| Сеть       | Назначение                           | Кто подключён                                                 |
|------------|--------------------------------------|---------------------------------------------------------------|
| `frontend` | Внешний доступ (клиент → gateway)    | gateway                                                       |
| `backend`  | Связь gateway ↔ микросервисы         | gateway, все бизнес-сервисы                                   |
| `data`     | Доступ к БД и кэшам                  | все сервисы, PostgreSQL, Redis, RabbitMQ, MongoDB, ClickHouse |

## Инфраструктурные сервисы

| Сервис             | Образ                          | Порт  | Назначение                                       |
|--------------------|--------------------------------|-------|--------------------------------------------------|
| `postgres_core`    | `postgres:17`                  | 5432  | Основная БД (учётные данные клиентов)            |
| `redis_sessions`   | `redis:7-alpine`               | 6379  | Сессионные токены (TTL 30 мин, healthcheck)      |
| `redis_onboarding` | `redis/redis-stack-server`     | 6379  | JSON-черновики + onboarding-токены (healthcheck) |
| `rabbitmq`         | `rabbitmq:3.13-management`     | 5672  | Брокер сообщений (уведомления, логи)             |
| `mongodb`          | `mongo:7`                      | 27017 | Журнал уведомлений (email_log, TTL 90 д)         |
| `postgres_history` | `postgres:17`                  | 5433  | БД истории действий пользователей (user_actions) |
| `clickhouse`       | `clickhouse-server:24`         | 8123  | Аналитика бизнес-событий (TTL 2 года)            |

> Все сервисы запускаются с `restart: unless-stopped`. Redis-сервисы имеют healthcheck (`redis-cli ping`), и зависимые сервисы ждут `condition: service_healthy`.

## Схема базы данных

Для PostgreSQL используется структура из 7 основных таблиц, описывающих профиль клиента (KYC) и банковские операции.

### ER-диаграмма (Подробная)
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

### Детальное описание таблиц
Подробное описание каждой таблицы, её полей и ограничений (CHECK, UNIQUE) находится в папке:
**[Документация БД](./docs/database/)**

- [users.md](./docs/database/users.md) — Основная таблица клиентов.
- [personal_data.md](./docs/database/personal_data.md) — Персональные данные.
- [passport.md](./docs/database/passport.md) — Паспортные данные.
- [identifiers.md](./docs/database/identifiers.md) — ИНН и СНИЛС.
- [contacts.md](./docs/database/contacts.md) — Контактные данные.
- [bank_accounts.md](./docs/database/bank_accounts.md) — Банковские счета.
- [transactions.md](./docs/database/transactions.md) — Транзакции.

## Запуск и инструменты

Для запуска всего Monorepo необходимо находиться в корневой папке бэкенда (`backend/`):

```bash
cd backend
docker compose up --build -d
```

Для запуска аудита
```bash
cd backend
docker compose run --rm audit
```

### Доступные интерфейсы:
- **API Gateway**: [http://localhost:8000](http://localhost:8000)
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **RabbitMQ Management**: [http://localhost:15672](http://localhost:15672)

---

## Тестирование

Система поддерживает универсальный метод запуска тестов для любого Python-сервиса через Docker Compose без необходимости настройки локального окружения.

```bash
# Запуск тестов для конкретного сервиса
docker compose run --rm -e APP_ENV=test <имя_сервиса>
```

**Пример (Account Service):**
`docker compose run --rm -e APP_ENV=test account_service`

**Механика работы в режиме APP_ENV=test:**
1. **Зависимости**: Контейнер автоматически доустанавливает библиотеки из `shared/requirements-test.txt`.
2. **База Данных**: `Bootstrap` переключает `DATABASE_URL` на тестовую БД (в экономном режиме это `bank_core_db`).
3. **Миграции**: Скрипт `migrations/reset_and_upgrade.py` полностью сбрасывает схему и накатывает миграции Alembic.
4. **Результат**: Тесты запускаются через `pytest` и выводят результат прямо в терминал.
