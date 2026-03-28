# Паттерны проекта
Документ фиксирует архитектурные решения, конвенции кода и принципы, принятые в проекте. Служит ориентиром при добавлении новых сервисов и рефакторинге существующих.

## 1. Архитектура

### 1.1 Микросервисы, а не монолит/SuperApp
Каждый бизнес-домен изолирован в отдельном сервисе со своим `Dockerfile`, `.env`, `requirements.txt`. Сервисы не импортируют код друг друга напрямую — общий код вынесен в пакет `shared/`.

### 1.2 API Gateway как единая точка входа
Клиент взаимодействует **только** с `gateway_service` (порт 8000). Gateway:
- проксирует запросы через `httpx.AsyncClient` (`forward_request`)
- выполняет аутентификацию (middleware) и PIN-gate
- инжектирует заголовки `X-Internal-Key` и `X-User-ID` перед пересылкой

Микросервисы **не экспонируют порты наружу** — доступны только внутри Docker-сети `backend`.

### 1.3 REST API
- Все эндпоинты следуют REST-конвенциям: ресурсы — существительные (`/accounts`, `/users`), действия — HTTP-методы
- Ответы — JSON. Статус-коды используются по назначению (`201` — создание, `409` — конфликт, `404` — не найден)
- Pydantic v2 для валидации входных и выходных данных


## 2. Аутентификация и безопасность

### 2.1 Трёхуровневая система аутентификации

| Уровень | Заголовок | Где проверяется | Назначение |
|---------|-----------|-----------------|------------|
| Сессия | `X-Session-Token` | Gateway (middleware) | Авторизованные пользователи |
| Онбординг | `X-Onboarding-Token` | Gateway (middleware) | Незавершённая регистрация |
| Внутренний ключ | `X-Internal-Key` | Микросервисы (`verify_internal_key`) | Защита от прямого доступа в обход gateway |

### 2.2 PIN-gate

После аутентификации по сессии middleware проверяет `has_pin` в Redis. Без установленного PIN доступны только `/auth/set-pin`, `/auth/logout`, `/auth/logout-all`. Все остальные роуты возвращают `403`.

### 2.3 Внутренний ключ (`X-Internal-Key`)

- Проверяется через `secrets.compare_digest()` (timing-safe, защита от timing-атак)
- Подключается на уровне `FastAPI(dependencies=[Depends(verify_internal_key)])`, а **не** на уровне отдельных роутеров — гарантирует, что ни один эндпоинт не окажется незащищённым
- Единственное исключение: `/health` — доступен без ключа (используется Docker healthcheck)

### 2.4 Изоляция Docker-сетей

| Сеть | Назначение | Доступ |
|------|------------|--------|
| `frontend` | Клиент → Gateway | Только gateway + notification_service |
| `backend` | Gateway ↔ микросервисы | gateway + все бизнес-сервисы |
| `data` | Сервисы → БД, кэши, брокеры | Все сервисы + вся инфраструктура |

Микросервисы не подключены к `frontend` → клиент физически не может обратиться к ним напрямую, даже зная порт.

### 2.5 Rate-limiting и блокировка

- PIN-попытки: 5 неудач → кулдаун 5 мин, 15 неудач → блокировка аккаунта + email
- Хранилище счётчиков — Redis (TTL, атомарные инкременты)
- Разблокировка через 6-значный код на email

## 3. Структура микросервиса

### 3.1 Файловая конвенция

```
<service>/
├── main.py              # FastAPI-app + lifespan (подключения к БД, брокерам)
├── exceptions.py        # Единая иерархия бизнес-исключений сервиса
├── <domain_module>/
│   ├── router.py        # FastAPI APIRouter, HTTP-обработчики
│   └── service.py       # Бизнес-логика, работа с БД
├── Dockerfile
├── requirements.txt
├── .env
└── README.md
```

### 3.2 Разделение router / service

- **`router.py`** — принимает HTTP-запрос, вызывает сервисный слой, маппит бизнес-исключения в HTTP-коды через `_raise()`. Не содержит SQL-запросов.
- **`service.py`** — чистая бизнес-логика и работа с БД через SQLAlchemy. Не знает о FastAPI (`HTTPException` не импортируется). Бросает бизнес-исключения из `exceptions.py`.

### 3.3 Единая иерархия исключений

Каждый сервис определяет свои исключения в `exceptions.py`, наследуя от одного базового:

```python
class AccountError(Exception): ...
class AccountNotFound(AccountError): ...
class AccountConflict(AccountError): ...
```

В роутере — единая функция `_raise()` для маппинга:

```python
def _raise(exc: AccountError) -> None:
    if isinstance(exc, AccountNotFound):
        raise HTTPException(404, detail=str(exc))
    if isinstance(exc, (AccountNotOpen, AccountConflict)):
        raise HTTPException(409, detail=str(exc))
    raise HTTPException(400, detail=str(exc))
```

Это исключает разрозненные `try/except` блоки и гарантирует единообразие HTTP-ответов.

### 3.4 Lifespan и подключения

Все внешние подключения (PostgreSQL, RabbitMQ, MongoDB) устанавливаются в `lifespan` и закрываются при остановке:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await rmq_connect()
    yield
    await rmq_disconnect()
    await engine.dispose()
```

---

## 4. Работа с данными

### 4.1 PostgreSQL — источник истины

- SQLAlchemy 2.0 с `AsyncSession` (asyncpg-драйвер)
- Сессия получается через `Depends(get_session)` — автоматический commit/rollback
- `IntegrityError` из SQLAlchemy ловится явно (а не `except Exception`) и преобразуется в бизнес-исключение (`AccountConflict`)

### 4.2 Redis — эфемерное хранилище

- **`redis_sessions`** (Redis 7): сессионные токены, TTL 30 мин, скользящая экспирация
- **`redis_onboarding`** (Redis Stack): JSON-черновики шагов регистрации, TTL 15 мин, скользящая экспирация
- Каждый экземпляр Redis изолирован — свой контейнер, свой порт

### 4.3 MongoDB — append-only журнал

- Коллекция `email_log` хранит все отправленные/неудавшиеся уведомления
- TTL-индекс на `created_at` — автоматическое удаление через 90 дней
- Async-драйвер `motor`

### 4.5 PostgreSQL History — аудит-лог действий

- Отдельный экземпляр PostgreSQL (`postgres_history`, порт 5433)
- Таблица `user_actions` — полный аудит действий пользователей (вход, PIN, счета, транзакции)
- DDL управляется через `HistoryBase.metadata.create_all` (не Alembic)
- Модуль: `shared/history_core` (SQLAlchemy async, `asyncpg`)

### 4.6 ClickHouse — аналитика бизнес-событий

- Таблица `business_events` (MergeTree, партиционирование по месяцам, TTL 2 года)
- Оптимизирована для аналитических запросов (колоночное хранение, LowCardinality)
- DDL создаётся при вызове `init_clickhouse()` (в lifespan log_service)
- Модуль: `shared/clickhouse_core` (`clickhouse-connect` async)

### 4.4 Alembic-миграции

- Миграции запускаются как отдельный контейнер (`migrations`) при `docker compose up`
- `depends_on: postgres_core: condition: service_healthy` — гарантия, что БД готова
- Dev-скрипт `reset_and_upgrade.py` для полного сброса при разработке

---

## 5. Межсервисное взаимодействие

### 5.1 Синхронное — HTTP через Gateway

Gateway проксирует запросы клиента к микросервисам через `httpx.AsyncClient`. Каждый сервис — отдельный `AsyncClient` в `app.state.services`, созданный в lifespan.

### 5.2 Асинхронное — RabbitMQ (events)

- **Exchange `notifications`** (topic, durable), routing key `email.send`
  - Публикация: `shared.rabbitmq.publish()` — fire-and-forget из любого сервиса
  - Потребление: `notification_service` — единственный consumer

- **Exchange `logs`** (topic, durable), routing keys `log.auth`, `log.account`, `log.transaction`
  - Публикация: `shared.rabbitmq.publish()` — fire-and-forget из бизнес-сервисов
  - Потребление: `log_service` — запись в PostgreSQL (history) + ClickHouse (analytics)

Формат сообщения (уведомления):
```json
{
  "type": "<имя_шаблона>",
  "payload": {
    "to": "user@example.com",
    "variables": { "key": "value" }
  }
}
```

Формат сообщения (бизнес-логи):
```json
{
  "type": "<категория>",
  "payload": {
    "user_id": "<uuid>",
    "action": "<действие>",
    "service": "<сервис>",
    "entity_id": "<uuid>",
    "entity_type": "<тип>",
    "amount": "<сумма>",
    "currency": "<валюта>",
    "status": "success",
    "details": "<описание>"
  }
}
```

### 5.3 Шаблоны уведомлений

Произвольные письма не отправляются. Каждый тип письма — зарегистрированный `EmailTemplate` в реестре `TEMPLATES`. Неизвестный `type` — логируется как warning и игнорируется.

---

## 6. Docker и инфраструктура

### 6.1 Docker Compose — единственный способ запуска

Все 20 сервисов (10 бизнес + 1 миграция + 9 инфра) описаны в одном `docker-compose.yaml`. Порядок запуска контролируется через `depends_on` + `condition: service_healthy / service_completed_successfully`.

### 6.2 Healthcheck

Каждый инфраструктурный сервис имеет healthcheck:
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- RabbitMQ: `rabbitmq-diagnostics check_port_connectivity`
- MongoDB: `mongosh --eval "db.adminCommand('ping')"`
- ClickHouse: `wget --spider -q http://localhost:8123/ping`

### 6.3 Restart policy

Все сервисы — `restart: unless-stopped`. Миграции — `restart: "no"` (one-shot).

### 6.4 Переменные окружения

- Инфраструктурные переменные (порты, пароли БД) — в корневом `.env`
- Сервисные переменные (DATABASE_URL, INTERNAL_API_KEY) — в `<service>/.env`
- Секреты в `.env` файлах, которые добавлены в `.gitignore`

---

## 7. Конвенции кода

### 7.1 Форматирование
- Табуляция для отступов (не пробелы)
- Строки документации — на русском языке
- Именование: snake_case для функций/переменных, PascalCase для классов

### 7.2 Логирование
- Каждый сервис создаёт `logger = logging.getLogger("<service_name>")`
- Формат: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Уровни: `INFO` для штатных операций, `WARNING` для нештатных но допустимых, `ERROR`/`EXCEPTION` для ошибок

### 7.3 Зависимости (Depends)
- `verify_internal_key` — на уровне `FastAPI(dependencies=...)`, не на роутере
- `require_user_id` — на уровне эндпоинта
- `get_session` — на уровне эндпоинта

### 7.4 Типизация
- `from __future__ import annotations` в модулях с forward references
- Type hints везде: параметры, возвращаемые значения, переменные уровня модуля

---

## 8. UI / Frontend (планируется)

### 8.1 Общие принципы
- Максимально удобный и простой интерфейс для пользователя
- Минимализм: нейтральная палитра, без агрессивных/кричащих цветов. Исключение — уведомления и предупреждения (жёлтый/красный для привлечения внимания)
- Информативность без перегруженности — каждый экран решает одну задачу

