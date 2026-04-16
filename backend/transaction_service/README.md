# Transaction Service

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.13-FF6600.svg)

Центральный сервис управления финансовыми операциями: пополнение, снятие, межбанковские переводы и предоставление истории операций.

## Архитектура

Сервис построен по принципам **Layered Architecture** (послойная архитектура) и строго следует 4-х слойной структуре (Routers, Services, Repositories, Core).

```text
transaction_service/
├── api/                # Слой Routers: эндпоинты (transactions, history)
├── services/           # Слой Services: бизнес-логика финансовых операций
├── repositories/       # Слой Repository: работа с БД и CQRS Query Layer
├── core/               # Инфраструктурный слой: config, uow, exceptions, shared utils
├── clients/            # Клиенты внешних микросервисов (currency, security)
├── main.py             # Точка входа в приложение
└── README.md
```

## Ключевые особенности

1.  **Атомарность**: Паттерн **Unit of Work** гарантирует целостность данных: либо перевод выполняется полностью для обеих сторон, либо происходит полный откат.
2.  **Антифрод и Безопасность**: Интеграция с `security_service` (AML-проверки). При подозрении на мошенничество счёт автоматически замораживается.
3.  **Cross-Currency**: Прозрачная конвертация валют (RUB/USD/EUR) через `currency_service` при переводах между счетами в разных валютах.
4.  **CQRS (Query Side)**: Высокопроизводительный слой чтения истории транзакций через сырой SQL, отделенный от бизнес-логики.
5.  **Идемпотентность**: Защита от повторных списаний при сбоях сети через клиентские ключи (`X-Idempotency-Key`).

## API Спецификация

Все внутренние запросы требуют заголовок `X-Internal-Key`.

| Метод | Путь                                | Описание                                       | Заголовки                  |
|-------|-------------------------------------|------------------------------------------------|----------------------------|
| POST  | `/transactions`                     | Создать операцию (пополнение, снятие, перевод) | `X-User-ID`, `X-Idempotency-Key` |
| GET   | `/accounts/{id}/transactions`       | История операций по конкретному счету          | `X-User-ID`                |
| GET   | `/health`                           | Глубокая проверка состояния сервиса (DB, RMQ)  | -                          |

## Доменные события (Domain Events)

| Событие               | Получатель (Exchange) | Описание                                   |
|-----------------------|-----------------------|--------------------------------------------|
| `transaction_transfer`| `notifications`       | Уведомление отправителю о переводе         |
| `transaction_incoming`| `notifications`       | Уведомление получателю о входящем платеже  |
| `transaction_deposit` | `notifications`       | Уведомление о пополнении баланса           |
| `transaction_withdrawal`| `notifications`      | Уведомление о снятии средств               |
| `transfer`            | `logs`                | Запись в аудит-лог (перевод)               |
| `deposit`             | `logs`                | Запись в аудит-лог (пополнение)            |
| `withdrawal`          | `logs`                | Запись в аудит-лог (снятие)                |

## Переменные окружения

| Ключ | Описание | Значение по умолчанию |
|------|----------|-----------------------|
| `APP_ENV` | Окружение (local, test, dev, prod) | `local` |
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgresql+asyncpg://...` |
| `CURRENCY_SERVICE_URL` | URL микросервиса валют | `http://currency_service:8000` |
| `SECURITY_SERVICE_URL` | URL микросервиса безопасности | `http://security_service:8000` |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | `amqp://guest:guest@localhost:5672/` |
| `INTERNAL_API_KEY` | Секретный ключ для межсервисных вызовов | - |

## Технологии
- **FastAPI**: API Framework.
- **SQLAlchemy (Async)**: Работа с БД через асинхронный ORM.
- **PostgreSQL**: Основное хранилище счетов и транзакций.
- **RabbitMQ**: Публикация событий (Domain Events).
- **Pydantic V2**: Валидация данных и управление настройками.
