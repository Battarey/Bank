# Log Service

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)
![ClickHouse](https://img.shields.io/badge/ClickHouse-24.3-FFCC00.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)

Системный микросервис для централизованного сбора, хранения и анализа событий (логов) всей банковской платформы. Реализует паттерн **Dual Write** для обеспечения аудита и аналитики.

## Архитектура

Сервис работает по событийному принципу (Event Consumer) и имеет облегченную API-прослойку для мониторинга.

```text
log_service/
├── api/                # Эндпоинты проверки состояния (Health Check)
├── workers/            # Консьюмеры RabbitMQ: обработка входящих событий
├── services/           # Логика обработки логов: парсинг, обогащение
├── repositories/       # Запись в PostgreSQL (Audit) и ClickHouse (Analytics)
├── core/               # Инфраструктура: config, container
├── main.py             # Точка входа в воркер
└── README.md
```

## Как это работает

1.  **Подписка**: Сервис слушает Exchange `logs` в RabbitMQ.
2.  **Обработка**: Каждое событие `LogEvent` проходит валидацию и типизацию.
3.  **Хранение (Dual Write)**:
    -   **PostgreSQL (History DB)**: Хранение критически важных событий аудита (входы, смены PIN, транзакции). Обеспечивает строгую консистентность и быстрый поиск по конкретному пользователю.
    -   **ClickHouse**: Высокопроизводительное хранилище для бизнес-аналитики (BI). Позволяет строить отчеты по оборотам, популярности услуг и нагрузке на систему.

## API Спецификация

| Метод | Путь       | Описание                                  | Заголовки |
|-------|------------|-------------------------------------------|-----------|
| GET   | `/health`  | Глубокая проверка состояния (DB, CH, RMQ) | -         |

## Обрабатываемые события (Subscribed Events)

Сервис подписывается на ключ `log.#` в Exchange `logs`.

| Источник (Routing Key)    | Описание                                   | Цель записи |
|---------------------------|--------------------------------------------|-------------|
| `log.account_service`     | Действия со счетами                        | Audit + BI  |
| `log.auth_service`        | События безопасности и входа               | Audit + BI  |
| `log.transaction_service` | Финансовые проводки                        | Audit + BI  |
| `log.customer_service`    | Изменения профилей                         | Audit       |
| `log.security_service`    | Нарушения AML и алерты                     | Audit       |

## Переменные окружения

| Ключ | Описание | Значение по умолчанию |
|------|----------|-----------------------|
| `APP_ENV` | Окружение (local, test, dev, prod) | `local` |
| `HISTORY_DATABASE_URL` | Хранилище аудита (PostgreSQL) | `postgresql+asyncpg://...` |
| `CLICKHOUSE_URL` | Хранилище аналитики | `http://clickhouse:8123` |
| `RABBITMQ_URL` | URL брокера для приема событий | `amqp://...` |
| `LOGS_EXCHANGE` | Название обменника логов | `logs` |

## Технологии
- **RabbitMQ (Aio-pika)**: Прием событий в асинхронном режиме.
- **ClickHouse**: Колоночная БД для сверхбыстрой аналитики.
- **PostgreSQL**: Хранилище истории операций (Audit trail).
- **FastAPI**: Легковес запуск Health-сервера.
