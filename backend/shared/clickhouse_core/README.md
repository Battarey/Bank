# ClickHouse Core

Async-клиент для ClickHouse — хранения бизнес-событий для аналитики и мониторинга. Используется `log_service` для записи структурированных логов.

## Файловая архитектура
```
clickhouse_core/
├── __init__.py    # Публичный API модуля
├── client.py      # Подключение, DDL, insert_log_event()
└── README.md
```

## Конфигурация

| Переменная           | Обязательна | Описание                     |
|----------------------|-------------|------------------------------|
| `CLICKHOUSE_HOST`    | Да          | Хост ClickHouse              |
| `CLICKHOUSE_PORT`    | Да          | HTTP-порт (8123)             |
| `CLICKHOUSE_USER`    | Да          | Пользователь                 |
| `CLICKHOUSE_PASSWORD`| Да          | Пароль                       |
| `CLICKHOUSE_DB`      | Да          | Имя базы данных              |

## Экспорт

| Символ             | Тип          | Описание                                              |
|--------------------|--------------|-------------------------------------------------------|
| `init_clickhouse`  | `coroutine`  | Подключение + создание таблицы `business_events`      |
| `close_clickhouse` | `coroutine`  | Закрытие соединения                                   |
| `insert_log_event` | `coroutine`  | Вставка одного бизнес-события                         |

## Таблица `business_events`

Создаётся автоматически при вызове `init_clickhouse()`.

| Колонка       | Тип ClickHouse                      | Описание                              |
|---------------|-------------------------------------|---------------------------------------|
| `id`          | `UUID` (default `generateUUIDv4()`) | Уникальный идентификатор              |
| `event_type`  | `LowCardinality(String)`           | Категория (auth, account, transaction) |
| `service`     | `LowCardinality(String)`           | Сервис-источник                        |
| `user_id`     | `UUID`                             | UUID пользователя                      |
| `entity_id`   | `Nullable(UUID)`                   | UUID связанной сущности                |
| `entity_type` | `LowCardinality(Nullable(String))` | Тип сущности                           |
| `action`      | `LowCardinality(String)`           | Действие (login, deposit и др.)        |
| `amount`      | `Nullable(Decimal(18, 2))`         | Сумма операции                         |
| `currency`    | `LowCardinality(Nullable(String))` | Валюта                                 |
| `status`      | `LowCardinality(String)`           | Результат (success, failed)            |
| `details`     | `Nullable(String)`                 | Дополнительная информация              |
| `ip_address`  | `Nullable(String)`                 | IP-адрес клиента                       |
| `created_at`  | `DateTime64(3, 'UTC')`             | Время события (default now64)          |

### Параметры таблицы
- **Engine:** `MergeTree()`
- **Партиционирование:** `toYYYYMM(created_at)` — по месяцам
- **Сортировка:** `(event_type, user_id, created_at)`
- **TTL:** `created_at + INTERVAL 2 YEAR` — автоматическое удаление через 2 года
- **Index granularity:** 8192

## Отличие от MongoDB

| Аспект       | MongoDB (`email_log`, `security_events`) | ClickHouse (`business_events`)         |
|--------------|------------------------------------------|----------------------------------------|
| Назначение   | Журнал уведомлений / AML-событий         | Аналитика *всех* бизнес-событий        |
| Хранение     | Документы (JSON)                         | Колоночное (MergeTree)                 |
| TTL          | 90 / 365 дней                            | 2 года                                 |
| Партиции     | Нет                                      | По месяцам                             |
| Оптимизация  | Гибкость схемы                           | Быстрые аналитические запросы          |
| Драйвер      | `motor` (async)                          | `clickhouse-connect` (async)           |
