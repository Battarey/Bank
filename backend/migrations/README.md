# Migrations (Alembic)

Сервис управления схемой реляционной базы данных PostgreSQL. Обеспечивает эволюцию структуры таблиц, индексацию и поддержание целостности данных через механизмы миграций.

---

## Файловая архитектура
```
migrations/
├── alembic/
│   ├── env.py            # Конфигурация подключения (Sync psycopg)
│   └── versions/         # История изменений схемы (Миграции)
├── postgre_core/         # DDL описание таблиц (Документация)
├── reset_and_upgrade.py  # Скрипт полной пересборки БД (только для Dev)
├── alembic.ini           # Глобальные настройки Alembic
└── Dockerfile            # Контейнер для автозапуска миграций
```

## История миграций (Chain of Revisions)

Основные этапы развития схемы данных:
1.  **`postgre_core_init`**: Создание базовых таблиц (users, accounts, transactions и др.).
2.  **`add_pin_hash`**: Внедрение захешированных PIN-кодов.
3.  **`add_freeze_columns`**: Поля для управления состоянием блокировки счетов.
4.  **`add_currency_and_metal`**: Расширение поддержки типов валют и драгметаллов.
5.  **`add_idempotency_key`**: Поле в транзакциях для предотвращения дублирования операций.
6.  **`add_pii_encryption`**: Механизмы шифрования персональных данных (PII) и слепых индексов для безопасного поиска.
7.  **`Indexing Phase`**: Добавление индексов на `client_id`, `account_id`, `created_at` и составных индексов для паспортов и транзакций.

---

## Составные части инфраструктуры

| База Данных         | Технология   | Назначение                                  |
|---------------------|--------------|---------------------------------------------|
| **PostgreSQL Core** | Alembic      | Транзакционные данные (Счета, Пользователи) |
| **Postgres History**| Meta.create  | Аудит действий ( user_actions)              |
| **Redis Sessions**  | Redis 7      | Активные сессии (X-Session-Token)           |
| **Redis Onboarding**| Redis Stack  | Черновики KYC (JSON)                        |
| **ClickHouse**      | MergeTree    | Бизнес-аналитика (business_events)          |
| **MongoDB**         | NoSQL        | Логи уведомлений и AML-событий              |

## Использование в Docker Compose

Миграции запускаются автоматически при старте окружения:
```yaml
migrations:
  image: bank-migrations
  depends_on:
    postgres_core:
      condition: service_healthy
  command: python reset_and_upgrade.py # Или alembic upgrade head
```

> Внимание: Скрипт `reset_and_upgrade.py` полностью удаляет схему `public` перед накатыванием миграций. Никогда не используйте его в Production окружении.
