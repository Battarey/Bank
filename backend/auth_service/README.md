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
4.  **Быстрый вход**: Использование **Rotating Refresh Tokens** (30 дней) для входа по PIN-коду без ввода номера телефона на доверенных устройствах.
5.  **Восстановление доступа**: Процесс «Забыли PIN?» через Email-OTP с обязательной установкой нового PIN-кода. Идентификация пользователя выполняется по номеру телефона.

## API Спецификация

Все внутренние запросы требуют заголовок `X-Internal-Key`.

| Метод  | Путь                         | Описание                                      | Заголовки |
|--------|------------------------------|-----------------------------------------------|-----------|
| POST   | `/sessions`                  | Вход (телефон + PIN) -> Выдача пары токенов   | -         |
| POST   | `/sessions/quick`            | Быстрый вход (Refresh Token + PIN)            | -         |
| DELETE | `/sessions/current`          | Выход (Logout текущей сессии)                 | -         |
| DELETE | `/sessions`                  | Сброс всех активных сессий пользователя       | -         |
| PUT    | `/pins`                      | Установка или изменение PIN-кода              | `X-User-ID` |
| POST   | `/sessions/me/block`         | Самоблокировка аккаунта                       | `X-User-ID` |
| POST   | `/unlock-codes`              | Запросить код восстановления (по Phone)       | -         |
| POST   | `/unlock-codes/verifications`| Подтвердить восстановление и сбросить PIN     | -         |
| GET    | `/health`                    | Проверка состояния сервиса                    | -         |

## Доменные события (Domain Events)

| Событие            | Получатель (Exchange) | Описание                                   |
|--------------------|-----------------------|--------------------------------------------|
| `pin_changed`      | `notifications`       | Уведомление о смене PIN-кода               |
| `unlock_code`      | `notifications`       | Отправка кода восстановления на Email      |
| `account_unlocked` | `notifications`       | Уведомление о разблокировке аккаунта       |
| `login`            | `logs`                | Успешный вход в систему (Phone + PIN)      |
| `quick_login`      | `logs`                | Быстрый вход (Refresh + PIN)               |
| `login_failure`    | `logs`                | Неудачная попытка входа (warning)          |
| `set_pin`          | `logs`                | Изменение настроек безопасности            |
| `recovery_success` | `logs`                | Успешное восстановление доступа и PIN      |

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
