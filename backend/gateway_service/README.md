# Gateway Service (Go)

API Gateway банковского приложения — единая точка входа для клиентских запросов.

## Стек
- **Язык:** Go 1.23
- **Фреймворк:** Echo v4
- **Redis-клиент:** go-redis v9
- **HTTP-клиент:** net/http (stdlib)

## Что делает

1. Принимает HTTP-запрос от клиента
2. **Middleware** проверяет `X-Session-Token` → Redis lookup → скользящая экспирация (TTL 30 мин)
3. **PIN-gate**: без установленного PIN доступны только `set-pin`, `logout`, `logout-all`
4. **Reverse proxy** пересылает запрос во внутренний сервис с инъекцией заголовков:
   - `X-Internal-Key` — защита от прямого доступа
   - `X-User-ID` — идентификатор пользователя из сессии
   - `X-Session-Token` — пробрасывается для auth_service

## Файловая структура

```
gateway_service/
├── main.go                 # Точка входа: конфиг, Echo, middleware, маршруты, graceful shutdown
├── config/                 # Загрузка переменных окружения
├── middleware/             # Auth middleware + PIN-gate
├── proxy/                  # Reverse-proxy (ForwardRequest / ForwardRaw)
├── redis/                  # Работа с Redis-клиентами сессий и онбординга
├── routes/                 # Утилита forwardAndParse, где хранятся пути к роутам
├── Dockerfile              # Multi-stage build (golang:1.23-alpine → alpine:3.19)
├── .env                    # Переменные окружения
├── go.mod                  # Go-модуль
└── go.sum                  # Хеши зависимостей
```

## Эндпоинты

### Публичные (без авторизации)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Healthcheck |
| POST | `/users/start` | Начать регистрацию |
| POST | `/auth/login-pin` | Вход по PIN |
| POST | `/auth/request-unlock` | Запрос кода разблокировки |
| POST | `/auth/unlock` | Разблокировка аккаунта |
| GET | `/currency/rates` | Курсы валют |
| GET | `/currency/rates/:base/:target` | Курс пары |
| GET | `/metals/rates` | Цены на металлы |

### Онбординг (X-Onboarding-Token)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/users/me/account/personal-data` | Шаг 1: ФИО |
| POST | `/users/me/account/passport` | Шаг 2: Паспорт |
| POST | `/users/me/account/identifiers` | Шаг 3: ИНН/СНИЛС |
| POST | `/users/me/account/contacts` | Шаг 4: Контакты |
| POST | `/users/me/account/send-email-code` | Код на email |
| POST | `/users/me/account/verify-email` | Подтверждение email |
| POST | `/users/me/account/finalize` | Завершение регистрации |

### Защищённые (X-Session-Token)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/set-pin` | Установить PIN |
| POST | `/auth/logout` | Выход |
| POST | `/auth/logout-all` | Выход со всех устройств |
| POST | `/auth/self-block` | Самоблокировка |
| POST | `/accounts` | Открыть счёт |
| GET | `/accounts` | Список счетов |
| GET | `/accounts/:id` | Детали счёта |
| POST | `/accounts/:id/close` | Закрыть счёт |
| POST | `/accounts/:id/freeze` | Заморозить счёт |
| POST | `/accounts/:id/unfreeze` | Разморозить счёт |
| POST | `/accounts/:id/deposit` | Пополнить |
| POST | `/accounts/:id/withdraw` | Снять |
| POST | `/accounts/:id/transfer` | Перевести |
| GET | `/accounts/:id/transactions` | История операций |
| POST | `/currency/exchange` | Обменять валюту |
| PATCH | `/users/me/personal-data` | Обновить ФИО |
| PUT | `/users/me/passport` | Заменить паспорт |
| PATCH | `/users/me/contacts` | Обновить контакты |
| DELETE | `/users/me` | Удалить аккаунт |

## Конфигурация и Маршрутизация

Gateway управляет всеми внешними запросами и пробрасывает их во внутренние сервисы.

Подробное описание:
- **[Карта эндпоинтов и маршрутизации (Gateway)](../../infra/README.md#доступные-интерфейсы)**
- **[Справочник переменных окружения](../../infra/env/README.md)**

## Docker

Multi-stage build: итоговый образ ~15 MB (Alpine).

```bash
docker compose build gateway_service
docker compose up gateway_service
```

## Совместимость с Redis

Go-версия gateway использует **идентичные Redis-ключи** с Python-сервисами:

- `session:token:{token}` — Hash (`user_id`, `has_pin`)
- `session:user:{userID}` — Set (активные токены пользователя)
есть пути - `onboarding:token:{token}` — String (user_id, TTL 15 мин)
