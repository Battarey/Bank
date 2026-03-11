# Backend для банковского приложения

## Стек
- **Языки:** Go 1.23 (Gateway), Python 3.12 (Бизнес-сервисы)
- **Фреймворки:** Echo (Go), FastAPI + asyncio (Python)
- **ORM / миграции:** SQLAlchemy 2.0 (async), Alembic
- **HTTP-клиент:** httpx (AsyncClient в Python сервисах)
- **Валидация:** Pydantic v2 (Python), go-swagger (Go)
- **БД:** PostgreSQL 17 (основная + история), Redis 7, Redis Stack, MongoDB 7, ClickHouse 24
- **Брокер:** RabbitMQ 3.13
- **Хеширование:** bcrypt (PIN-коды)
- **Контейнеризация:** Docker, Docker Compose
- **Тесты:** Pytest (в процессе)

## Файловая архитектура
```
bank/
├── gateway_service/             # API Gateway (Go) — единая точка входа, маршрутизация, аутентификация
├── customer_service/            # Онбординг и управление данными клиента (ФИО, паспорт, контакты)
├── auth_service/                # Аутентификация: логин по PIN, сессии, установка PIN, самоблокировка
├── account_service/             # Сервис банковских счетов: открытие, просмотр, закрытие, заморозка
├── currency_service/            # Сервис валютных операций: курсы (ExchangeRate API), обмен между счетами
├── log_service/                 # Сервис логирования: RabbitMQ consumer → PostgreSQL (history) + ClickHouse (analytics)
├── metal_service/               # Сервис драгоценных металлов: цены (Metals.Dev API)
├── notification_service/        # Сервис уведомлений: RabbitMQ consumer → SMTP (email по шаблонам)
├── transaction_service/         # Сервис транзакций: пополнение, снятие, переводы, история + AML-проверка
├── security_service/            # AML / антифрод: 6 правил, автозаморозка, журнал в MongoDB
├── migrations/                  # Alembic-миграции + dev-скрипт сброса БД
├── shared/                      # Общий пакет: модели, схемы, Redis-клиенты, утилиты, внутренняя аутентификация
└── docker-compose.yaml          # 22 сервиса: 12 бизнес + 1 миграция + 9 инфраструктура
```

## Архитектура

```
                  ┌───────────────┐
   Клиент ──────► │    Gateway    │ :8000
                  └──┬───┬─────┬─┬┘
                     │   │     │ └────────┐ 
          ┌──────────┘   │     └──────┐   └────────────┐
          │              │            │                │
          ▼              ▼            ▼                ▼
   ┌─────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐
   │  Customer   │ │   Auth   │ │  Account   │ │ Transaction  │
   │   Service   │ │  Service │ │  Service   │ │   Service    │
   └──────┬──────┘ └─────┬────┘ └───────┬────┘ └───────┬──────┘
          │              │              │              │
          │              │              │          ┌───┘
          │              │              │          ▼
          │              │              │   ┌──────────────┐
          │              │              │   │   Security   │
          │              │              │   │   Service    │
          │              │              │   │  (AML/CFT)   │
          │              │              │   └──────┬───────┘
          │              │              │          │
          ▼              ▼              ▼          ▼
   ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐
   │  PostgreSQL │ │    Redis    │ │      RabbitMQ         │
   │   (core)    │ │ sessions /  │ │                       │
   │             │ │ onboarding  │ │   ┌─────────┐ ┌──────┐│
   └─────────────┘ └─────────────┘ │   │notifica-│ │ logs ││
                                   │   │  tions  │ │      ││
                                   │   └────┬────┘ └──┬───┘│
                                   └────────┼─────────┼────┘
                                            │         │
   ┌──────────────┐ ┌──────────────┐        ▼         ▼
   │   Currency   │ │    Metal     │ ┌────────────┐ ┌──────────┐
   │   Service    │ │   Service    │ │Notification│ │   Log    │
   │ (ExchangeRate│ │ (Metals.Dev  │ │  Service   │ │  Service │
   │     API)     │ │     API)     │ │ (consumer) │ │(consumer)│
   └──────────────┘ └──────────────┘ └──┬───────┬─┘ └──┬────┬──┘
                                        │       │      │    │
                                        ▼       ▼      ▼    ▼
                                  Gmail SMTP  MongoDB  PG   ClickHouse
                                             (email_log  (history)
                                           + security)
```

### Сети Docker

| Сеть       | Назначение                           | Кто подключён                                                 |
|------------|--------------------------------------|---------------------------------------------------------------|
| `frontend` | Внешний доступ (клиент → gateway)    | gateway                                                       |
| `backend`  | Связь gateway ↔ микросервисы         | gateway, все бизнес-сервисы                                   |
| `data`     | Доступ к БД и кэшам                  | все сервисы, PostgreSQL, Redis, RabbitMQ, MongoDB, ClickHouse |

### Инфраструктура

| Сервис             | Образ                          | Порт  | Назначение                                       |
|--------------------|--------------------------------|-------|--------------------------------------------------|
| `postgres_core`    | `postgres:17`                  | 5432  | Основная БД (учётные данные клиентов)            |
| `redis_sessions`   | `redis:7-alpine`               | 6379  | Сессионные токены (TTL 30 мин, healthcheck)      |
| `redis_onboarding` | `redis/redis-stack-server`     | 6379  | JSON-черновики + onboarding-токены (healthcheck) |
| `rabbitmq`         | `rabbitmq:3.13-management`     | 5672  | Брокер сообщений (уведомления, логи)             |
| `mongodb`          | `mongo:7`                      | 27017 | Журнал уведомлений (email_log, TTL 90 д)         |
| `postgres_history` | `postgres:17`                  | 5433  | БД истории действий пользователей (user_actions) |
| `clickhouse`       | `clickhouse-server:24`         | 8123  | Аналитика бизнес-событий (TTL 2 года)            |
| `pgadmin`          | `dpage/pgadmin4`               | 5050  | Веб-интерфейс для PostgreSQL                     |
| `mongo_express`    | `mongo-express:latest`         | 8081  | Веб-интерфейс для MongoDB                        |

> Все сервисы запускаются с `restart: unless-stopped`. Redis-сервисы имеют healthcheck (`redis-cli ping`), и зависимые сервисы ждут `condition: service_healthy`.

## Аутентификация

Проект использует три механизма аутентификации:

| Механизм               | Заголовок            | Где проверяется | Назначение                                |
|------------------------|----------------------|-----------------|-------------------------------------------|
| Сессионный токен       | `X-Session-Token`    | Gateway         | Авторизованные пользователи               |
| Onboarding-токен       | `X-Onboarding-Token` | Gateway         | Незавершённая регистрация                 |
| Внутренний ключ        | `X-Internal-Key`     | Микросервисы    | Защита от прямого доступа в обход gateway |

## Реализованные сервисы

### Gateway Service (Go)
- Высокопроизводительный Reverse Proxy (Echo Framework)
- Маршрутизация запросов к внутренним Python-микросервисам
- Middleware аутентификации (сессии + onboarding-токены) через go-redis
- PIN-gate: без установленного PIN доступны только `/auth/set-pin`, `/auth/logout`, `/auth/logout-all`
- CORS-настройки
- Swagger UI с автозаполнением DTO-схем и двумя схемами авторизации

### Customer Service
- Онбординг: `/users/start` → 4 шага → `/users/me/account/finalize`
- Шаги: персональные данные, паспорт, идентификаторы (ИНН/СНИЛС), контакты
- Email-верификация: `send-email-code` → `verify-email` (через RabbitMQ → notification_service)
- Черновики шагов хранятся в Redis Stack (JSON, TTL 24 ч)
- Onboarding-токен: TTL 15 мин, скользящая экспирация (продлевается при каждом шаге)
- Повторный ввод шага — черновик перезаписывается
- При завершении регистрации отправляется приветственное письмо (`welcome`)
- Обновление данных авторизованного пользователя: `/users/me/personal-data`, `/users/me/passport`, `/users/me/contacts`
- **Удаление аккаунта (soft delete):** `DELETE /users/me` — статус → `deleted`, каскадная заморозка счетов, отзыв сессий, email-уведомление. Данные сохраняются в БД

### Auth Service
- Логин по PIN: `/auth/login-pin` + email-уведомление о входе (`login_alert`)
- Установка / смена PIN: `/auth/set-pin` + email-уведомление (`pin_changed`)
- Выход: `/auth/logout`, `/auth/logout-all`
- **Самоблокировка:** `/auth/self-block` — блокирует аккаунт, каскадно замораживает все счета, завершает все сессии
- bcrypt для хеширования PIN, сессии в Redis (TTL 30 мин, скользящая экспирация)
- **Rate-limiting PIN:** 5 неудач → кулдаун 5 мин, 3× = 15 неудач → блокировка аккаунта + каскадная заморозка счетов + email-уведомление
- **Разблокировка:** `/auth/request-unlock` → код на email → `/auth/unlock` + каскадная разморозка системных заморозок

### Notification Service
- RabbitMQ consumer (не HTTP-сервис)
- Email-шаблоны: `verification_code`, `welcome`, `pin_changed`, `login_alert`, `account_locked`, `unlock_code`, `account_unlocked`, `account_opened`, `account_closed`, `account_frozen`, `account_unfrozen`, `account_self_blocked`, `account_deleted`, `security_freeze`, `transaction_deposit`, `transaction_withdrawal`, `transaction_transfer`, `transaction_incoming`
- SMTP-транспорт через aiosmtplib (Gmail)
- Журнал уведомлений в MongoDB (коллекция `email_log`, TTL 90 дней)
- Произвольные письма не отправляются — только зарегистрированные шаблоны

### Log Service
- RabbitMQ consumer (не HTTP-сервис), аналогично notification_service
- Подписка на exchange `logs` (binding `log.#`)
- Дуальная запись каждого события:
  - **PostgreSQL (history):** таблица `user_actions` — полный аудит действий пользователей
  - **ClickHouse:** таблица `business_events` — аналитика (MergeTree, TTL 2 года, партиционирование по месяцам)
- События: аутентификация, регистрация, операции со счетами, транзакции
- Shared-модули: `shared/history_core` (SQLAlchemy async), `shared/clickhouse_core` (clickhouse-connect)

### Shared
- ORM-модели: `User`, `PersonalData`, `Passport`, `Identifier`, `Contact`, `BankAccount` (+ frozen_by/frozen_at/freeze_reason), `Transaction` (+ balance_before/balance_after)
- Pydantic-схемы для всех запросов/ответов (13 файлов: auth, bank_account, contacts, currency, email_verification, identifiers, metal, onboarding, passport, personal_data, transaction, unlock, schemas)
- Redis-клиенты для сессий и онбординга
- RabbitMQ-клиент (aio-pika): `connect`, `disconnect`, `publish`
- History Core: async-клиент PostgreSQL для истории действий (модель `UserAction`)
- ClickHouse Core: async-клиент для аналитики бизнес-событий
- Зависимости: `verify_internal_key()` (timing-safe), `require_user_id()`
- Утилиты нормализации: `normalize_name`, `normalize_email`, `normalize_phone`, `digits_only`

### Migrations
- Alembic с синхронным драйвером `psycopg`
- Dev-скрипт `reset_and_upgrade.py` для полного сброса
- 9 миграций, 7 таблиц + CHECK-ограничения + индексы (составные и простые)
- ER-диаграммы в `postgre_core/`

### Account Service
- Открытие счёта: `POST /accounts` (checking, savings, credit, deposit × RUB, USD, EUR)
- Генерация 20-значного номера по стандарту (код типа + валюта + контрольная цифра + отделение + индивидуальный)
- Лимит: не более 3 открытых счетов на комбинацию тип + валюта
- Просмотр: `GET /accounts`, `GET /accounts/{id}`
- Закрытие: `POST /accounts/{id}/close` (только при балансе 0)
- **Заморозка:** `POST /accounts/{id}/freeze` — soft-freeze (входящие разрешены, исходящие заблокированы)
- **Разморозка:** `POST /accounts/{id}/unfreeze` — доступна только для user-frozen (не системных)
- Каскадная заморозка / разморозка при блокировке / разблокировке аккаунта

### Transaction Service
- Пополнение: `POST /accounts/{id}/deposit`
- Снятие: `POST /accounts/{id}/withdraw` (проверка баланса)
- Перевод: `POST /accounts/{id}/transfer` (собственные / чужие счета, автоконвертация при разных валютах через Currency Service)
- История: `GET /accounts/{id}/transactions` (пагинация, фильтры по типу/направлению)
- Row-level locking (`FOR UPDATE`) на всех мутациях баланса
- Deadlock prevention: упорядоченная блокировка UUID при переводах
- **AML-проверка:** перед каждым снятием / переводом вызывается security_service (fail-open)
- **Автозаморозка:** при срабатывании AML-правил счёт замораживается (`frozen_by = "system"`)
- Email-уведомления на все операции через RabbitMQ

### Currency Service
- Просмотр курсов: `GET /rates?base=RUB` (все валюты), `GET /rates/{base}/{target}` (пара)
- Обмен между счетами: `POST /exchange` — конвертация между RUB/USD/EUR счетами пользователя
- Данные из ExchangeRate API, in-memory кэш (TTL 30 сек для просмотра, 60 сек для обмена)
- Row-level locking на обоих счетах при обмене, deadlock prevention (упорядоченная блокировка UUID)
- Email-уведомления и логирование через RabbitMQ

### Metal Service
- Просмотр цен: `GET /metals/rates?base=RUB` — цены XAU/XAG/XPT/XPD за грамм
- Данные из Metals.Dev API (`unit=g`), in-memory кэш (TTL 30 сек)
- Не использует БД — чистый API-прокси

### Security Service
- Внутренний сервис AML / антифрод-проверок (не доступен через Gateway)
- 6 AML-правил: крупная транзакция, суточный объём, суточный лимит операций, rapid-fire, дробление (structuring), серия круглых сумм
- Пороговые значения настраиваются через переменные окружения
- Журнал событий в MongoDB (`bank_security_db.security_events`, TTL 365 дней)
- Fail-open: при недоступности сервиса транзакции проходят

## Запуск

```bash
docker compose up --build
```

Gateway будет доступен на `http://localhost:8000`.
Swagger UI: `http://localhost:8000/docs`.
pgAdmin: `http://localhost:5050`.
Mongo Express: `http://localhost:8081`.

## TODO

### Глобальный
- Вклады/накопительный счёт

### Test
- Создать тестовые env
- Покрыть тестами (unit/integrations/нагрузка)

### Front
- Frontend
- Telegram APP (Для информативных функций, безопасность)

### END
- Лицензирования кода (MIT, Apache 2.0, GPL v3)
