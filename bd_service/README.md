# Сервис для работы с БД

## Файловая архитектура
```
bd_service
├── alembic/                     #
├── postgre_core/                # Папка, где хранятся md файлы с информацией про таблицы, название файла - название таблицы
└── alembic.ini                  # 
```

## Выбор БД
 Для хранения полей и пользователской информации используется Postgre. В Postgre будут следующие БД: 
  1. Учётные данные пользователя - postgre_core
  2. История операций пользователя (Потом)
 Для хранения логов используется ClickHouse. (Потом)
 Для хранения токенов используется Redis.
 Для хранения уведомлений MongoDB. (Потом)

## ER-диаграммы

### postgre_core

####  Простая вресия
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

### Подробная версия
````mermaid
erDiagram
    USERS {
        UUID id PK
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TEXT status
        BOOLEAN is_verified
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
- Связи `||` обозначают связь один-к-одному (client_id — уникальный для KYC-таблиц).
- `o{` показывает связь один-ко-многим: у клиента несколько счетов, у счёта много транзакций.
- `related_account_id` используется только для переводов, поэтому связь пунктирно отражает возможную ссылку на второй счёт.

Проверка диаграммы - https://mermaid.live

## Alembic
 Команды:
    - `alembic revision -m "init"` — создать новую миграцию (правь файлы в `alembic/versions`).
    - `alembic upgrade head` — применить все миграции.
    - `alembic downgrade -1` — откатить последнюю миграцию.
