# History Core

Асинхронное подключение к PostgreSQL History — отдельная база данных для аудит-лога действий пользователей. Используется `log_service` для записи всех бизнес-событий.

## Файловая архитектура
```
history_core/
├── env.py         # Чтение HISTORY_DATABASE_URL из окружения
├── db.py          # AsyncEngine, HistorySessionLocal, get_history_session()
├── models.py      # ORM-модель UserAction (таблица user_actions)
└── README.md
```

## Экспорт

| Символ                | Тип                                    | Описание                                           |
|-----------------------|----------------------------------------|----------------------------------------------------|
| `HistoryBase`         | `DeclarativeBase`                      | Базовый класс для моделей postgres_history         |
| `UserAction`          | `DeclarativeBase`                      | ORM-модель аудит-лога (таблица `user_actions`)     |
| `history_engine`      | `AsyncEngine`                          | Асинхронный движок SQLAlchemy                      |
| `HistorySessionLocal` | `async_sessionmaker[AsyncSession]`     | Фабрика сессий                                     |
| `get_history_session` | `AsyncGenerator[AsyncSession, None]`   | FastAPI Depends — открывает и закрывает сессию     |

## Модель `UserAction` — таблица `user_actions`

Аудит-лог действий пользователя. Хранит все значимые события: вход, смена PIN, операции со счетами, транзакции, блокировки.

| Колонка       | Тип             | Ограничения                    | Описание                                    |
|---------------|-----------------|--------------------------------|---------------------------------------------|
| `id`          | `UUID`          | PK, default `uuid4`            | Уникальный идентификатор записи             |
| `user_id`     | `UUID`          | NOT NULL, indexed              | Кто выполнил действие                       |
| `action`      | `Text`          | NOT NULL, indexed              | Тип действия (login, deposit и др.)         |
| `service`     | `Text`          | NOT NULL                       | Сервис-источник                             |
| `details`     | `Text`          | nullable                       | Произвольные детали действия                |
| `entity_id`   | `UUID`          | nullable                       | UUID связанной сущности (счёт, транзакция)  |
| `entity_type` | `Text`          | nullable                       | Тип сущности (bank_account, transaction)    |
| `amount`      | `Numeric(18,2)` | nullable                       | Сумма (для финансовых операций)             |
| `currency`    | `Text`          | nullable                       | Валюта                                      |
| `status`      | `Text`          | NOT NULL, default `success`    | Результат (success, failed, blocked)        |
| `ip_address`  | `Text`          | nullable                       | IP-адрес клиента                            |
| `created_at`  | `DateTime(tz)`  | NOT NULL, indexed, default now | Время события                               |

## Отличие от database_core

| Аспект          | `database_core`             | `history_core`                    |
|-----------------|-----------------------------|-----------------------------------|
| БД              | `postgres_core` (порт 5432) | `postgres_history` (порт 5433)    |
| Назначение      | Учётные данные клиентов     | Аудит-лог действий                |
| Таблицы         | 7 (через Alembic)           | 1 (`user_actions`, auto-create)   |
| Управление DDL  | Alembic-миграции            | `HistoryBase.metadata.create_all` |
| Кто использует  | Все бизнес-сервисы          | `log_service`                     |
