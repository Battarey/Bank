# Backend для банковского приложения

## Стек
- **Язык:** Python 3.12
- **Фреймворк:** FastAPI, asyncio
- **ORM / миграции:** SQLAlchemy 2.0 (async), Alembic
- **HTTP-клиент:** httpx (AsyncClient)
- **Валидация:** Pydantic v2
- **БД:** PostgreSQL 17, Redis 7, Redis Stack
- **Брокер:** RabbitMQ 3.13
- **Хеширование:** bcrypt (PIN-коды)
- **Контейнеризация:** Docker, Docker Compose
- **Тесты:** Pytest (в процессе)

## Файловая архитектура
```
bank/
├── gateway_service/             # API Gateway — единая точка входа, маршрутизация, аутентификация
├── customer_service/            # Онбординг и управление данными клиента (ФИО, паспорт, контакты)
├── auth_service/                # Аутентификация: логин по PIN, сессии, установка PIN
├── account_service/             # Сервис банковских счетов (заглушка)
├── currency_service/            # Сервис иностранных валют (заглушка)
├── log_service/                 # Сервис логирования (заглушка)
├── metal_service/               # Сервис драг. металлов (заглушка)
├── notification_service/        # Сервис уведомлений: RabbitMQ consumer → SMTP (email по шаблонам)
├── transaction_service/         # Сервис транзакций (заглушка)
├── migrations/                  # Alembic-миграции + dev-скрипт сброса БД
├── shared/                      # Общий пакет: модели, схемы, Redis-клиенты, внутренняя аутентификация
├── docker-compose.yaml          # 14 сервисов: 9 бизнес + 5 инфраструктура
├── .env                         # Переменные окружения инфраструктуры
└── README.md
```

## Архитектура

```
                  ┌───────────────┐
   Клиент ──────► │    Gateway    │ :8000
                  └──┬────┬───┬──┘
                     │    │   │
          ┌──────────┘    │   └──────────┐
          ▼               ▼              ▼
   ┌─────────────┐ ┌────────────┐ ┌──────────────┐
   │  Customer   │ │    Auth    │ │  Account...  │
   │   Service   │ │   Service  │ │  (заглушки)  │
   └──────┬──────┘ └─────┬──────┘ └──────────────┘
          │               │
          ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌──────────────┐
   │  PostgreSQL │ │    Redis    │ │   RabbitMQ   │
   │    (core)   │ │ sessions /  │ │              │
   │             │ │ onboarding  │ │      ▼       │
   └─────────────┘ └─────────────┘ │ Notification │
                                   │   Service    │
                                   │  (consumer)  │
                                   └──────┬───────┘
                                          ▼
                                     Gmail SMTP
```

### Сети Docker

| Сеть       | Назначение                           | Кто подключён                      |
|------------|--------------------------------------|------------------------------------|
| `frontend` | Внешний доступ (клиент → gateway)    | gateway                           |
| `backend`  | Связь gateway ↔ микросервисы         | gateway, все бизнес-сервисы       |
| `data`     | Доступ к БД и кэшам                 | все сервисы, PostgreSQL, Redis, RabbitMQ |

### Инфраструктура

| Сервис             | Образ                          | Порт  | Назначение                              |
|--------------------|--------------------------------|-------|-----------------------------------------|
| `postgres_core`    | `postgres:17`                  | 5432  | Основная БД (учётные данные клиентов)   |
| `redis_sessions`   | `redis:7-alpine`               | 6379  | Сессионные токены (TTL 30 мин)          |
| `redis_onboarding` | `redis/redis-stack-server`     | 6379  | JSON-черновики + onboarding-токены       |
| `rabbitmq`         | `rabbitmq:3.13-management`     | 5672  | Брокер сообщений (уведомления, логи)    |
| `pgadmin`          | `dpage/pgadmin4`               | 80    | Веб-интерфейс для PostgreSQL            |

## Аутентификация

Проект использует три механизма аутентификации:

| Механизм              | Заголовок            | Где проверяется | Назначение                         |
|------------------------|----------------------|-----------------|------------------------------------|
| Сессионный токен       | `X-Session-Token`    | Gateway         | Авторизованные пользователи        |
| Onboarding-токен       | `X-Onboarding-Token` | Gateway         | Незавершённая регистрация           |
| Внутренний ключ        | `X-Internal-Key`     | Микросервисы    | Защита от прямого доступа в обход gateway |

## Реализованные сервисы

### Gateway Service
- Маршрутизация запросов к микросервисам через httpx
- Middleware аутентификации (сессии + onboarding-токены)
- CORS-настройки
- Swagger UI с двумя схемами авторизации

### Customer Service
- Онбординг: `/users/start` → 4 шага → `/users/me/account/finalize`
- Шаги: персональные данные, паспорт, идентификаторы (ИНН/СНИЛС), контакты
- Email-верификация: `send-email-code` → `verify-email` (через RabbitMQ → notification_service)
- Черновики шагов хранятся в Redis Stack (JSON, TTL 60 мин)
- Повторный ввод шага — черновик перезаписывается
- Обновление данных авторизованного пользователя: `/users/me/personal-data`, `/users/me/passport`, `/users/me/contacts`

### Auth Service
- Логин по PIN: `/auth/login-pin`
- Установка / смена PIN: `/auth/set-pin`
- Выход: `/auth/logout`, `/auth/logout-all`
- bcrypt для хеширования PIN, сессии в Redis (TTL 30 мин)

### Notification Service
- RabbitMQ consumer (не HTTP-сервис)
- Email-шаблоны: `verification_code`, `welcome`, `pin_changed`, `login_alert`
- SMTP-транспорт через aiosmtplib (Gmail)
- Произвольные письма не отправляются — только зарегистрированные шаблоны

### Shared
- ORM-модели: `User`, `PersonalData`, `Passport`, `Identifier`, `Contact`
- Pydantic-схемы для всех запросов/ответов
- Redis-клиенты для сессий и онбординга
- RabbitMQ-клиент (aio-pika): `connect`, `disconnect`, `publish`
- Зависимости: `verify_internal_key()`, `require_user_id()`

### Migrations
- Alembic с синхронным драйвером `psycopg`
- Dev-скрипт `reset_and_upgrade.py` для полного сброса
- 7 таблиц + CHECK-ограничения
- ER-диаграммы в `postgre_core/`

## Запуск

```bash
docker compose up --build
```

Gateway будет доступен на `http://localhost:8000`.
Swagger UI: `http://localhost:8000/docs`.
pgAdmin: `http://localhost:5050`.

## TODO
- account_service — открытие / закрытие счетов
- transaction_service — переводы, пополнения, списания
- delete_account — удаление аккаунта клиента
- Покрыть тестами customer_service и auth_service
- currency_service — курсы валют
- metal_service — драг. металлы
- log_service — логирование через RabbitMQ + ClickHouse
