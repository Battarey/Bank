# Auth Service

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)
![Redis](https://img.shields.io/badge/Redis-7--alpine-D82C20.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)

Микросервис аутентификации и управления сессиями. Отвечает за вход по PIN-коду, безопасность аккаунтов, блокировку и восстановление доступа.

## Архитектура

Сервис построен по принципам **Layered Architecture** и строго следует 4-х слойной структуре (api, services, repositories, core).

```text
auth_service/
├── api/                # Слой API: вход, сессии, разблокировка
├── services/           # Слой Services: бизнес-логика аутентификации
├── repositories/       # Слой Repository: работа с данными пользователей
├── core/               # Инфраструктурный слой: uow, exceptions
├── main.py             # Точка входа в приложение
└── README.md
```

## Ключевые особенности

1.  **Атомарность**: Использование паттерна **Unit of Work** для гарантированной консистентности при смене PIN или блокировке.
2.  **Безопасность**: Хеширование (bcrypt), слепые индексы для поиска и защита от брутфорса через Redis Rate-Limiting.
3.  **Сессионная модель**: Хранение активных сессий в Redis с поддержкой отзыва (Logout/Revoke All).
4.  **Разблокировка**: Многофакторное восстановление доступа через Email-коды.

## API Спецификация

Все внутренние запросы требуют заголовок `X-Internal-Key`.

| Метод  | Путь                         | Описание                                  | Заголовки |
|--------|------------------------------|-------------------------------------------|-----------|
| POST   | `/sessions`                  | Вход (телефон + PIN) -> Выдача токена     | -         |
| DELETE | `/sessions/current`          | Выход (Logout текущей сессии)             | -         |
| DELETE | `/sessions`                  | Сброс всех активных сессий пользователя   | -         |
| PUT    | `/pins`                      | Установка или изменение PIN-кода          | `X-User-ID` |
| POST   | `/sessions/me/block`         | Самоблокировка аккаунта                   | `X-User-ID` |
| POST   | `/unlock-codes`              | Запросить 6-значный код для разблокировки | -         |
| POST   | `/unlock-codes/verifications`| Подтвердить разблокировку по коду         | -         |
| GET    | `/health`                    | Проверка состояния сервиса                | -         |

## Доменные события (Domain Events)

| Событие            | Получатель (Exchange) | Описание                                   |
|--------------------|-----------------------|--------------------------------------------|
| `pin_changed`      | `notifications`       | Уведомление о смене PIN-кода               |
| `unlock_code`      | `notifications`       | Отправка кода разблокировки                |
| `account_unlocked` | `notifications`       | Уведомление о разблокировке аккаунта       |
| `login`            | `logs`                | Успешный вход в систему                    |
| `login_failure`    | `logs`                | Неудачная попытка входа (warning)          |
| `set_pin`          | `logs`                | Изменение настроек безопасности            |
| `unlock_request`   | `logs`                | Запрос на восстановление доступа           |
| `unlock`           | `logs`                | Успешное восстановление доступа            |

## Переменные окружения

| Ключ | Описание | Значение по умолчанию |
|------|----------|-----------------------|
| `APP_ENV` | Окружение (local, test, dev, prod) | `local` |
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgresql+asyncpg://...` |
| `REDIS_SESSIONS_URL` | URL подключения к Redis (Sessions) | `redis://localhost:6379/0` |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | `amqp://guest:guest@localhost:5672/` |
| `INTERNAL_API_KEY` | Секретный ключ для межсервисных вызовов | - |

## Технологии
- **FastAPI**: Фреймворк API.
- **Redis**: Хранилище сессий и счетчиков попыток.
- **SQLAlchemy 2.0**: Работа с БД (Postgres).
- **Bcrypt**: Хеширование PIN-кодов.
- **RabbitMQ**: Доменные события.
