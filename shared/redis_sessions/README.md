# Redis Sessions

Модуль для работы с сессионными токенами, rate-limiting PIN-кода и кодами разблокировки в Redis.

## Файловая архитектура
```
redis_sessions/
├── client.py         # Синглтон-клиент Redis (REDIS_SESSIONS_URL)
├── tokens.py         # CRUD для сессионных токенов (save / load / delete / revoke_all)
├── dependencies.py   # authenticate_token(), verify_session_token()
├── rate_limit.py     # Rate-limiter для PIN-аутентификации
└── unlock_codes.py   # Коды разблокировки аккаунта
```

## Конфигурация

| Переменная           | Обязательна | Описание                                          |
|----------------------|-------------|----------------------------------------------------|
| `REDIS_SESSIONS_URL` | Да          | URL Redis (например `redis://redis_sessions:6379`) |

Если переменная не задана, при импорте выводится `warnings.warn`, а при обращении к клиенту — ошибка.

## Ключи Redis

| Паттерн                        | Тип    | TTL    | Описание                                     |
|---------------------------------|--------|--------|----------------------------------------------|
| `session:token:{token}`         | Hash   | 30 мин* | Данные сессии (`user_id` + payload)           |
| `session:user:{user_id}`        | Set    | 30 мин* | Множество активных токенов пользователя       |

> \* Скользящая экспирация — TTL продлевается при каждом запросе. 30 минут отсчитываются от последнего действия.
| `rate:pin:{phone}:total`        | String | —      | Счётчик неудачных попыток ввода PIN           |
| `rate:pin:{phone}:cooldown`     | String | 5 мин  | Флаг кулдауна                                |
| `unlock:{user_id}:code`         | String | 10 мин | 6-значный код разблокировки                   |

## Экспорт

### `client.py`

| Символ           | Описание                                         |
|------------------|--------------------------------------------------|
| `get_client()`   | Возвращает синглтон `redis.asyncio.Redis`        |
| `close_client()` | Закрывает пул соединений (вызывается при остановке) |

### `tokens.py`

| Символ            | Описание                                                     |
|-------------------|--------------------------------------------------------------|
| `DEFAULT_SESSION_TTL` | `timedelta(minutes=30)`                                 |
| `save_token()`    | Сохранить токен → user_id + payload, добавить в set пользователя |
| `load_token()`    | Получить данные сессии по токену (или `None`)                 |
| `touch_token()`   | Продлить TTL токена + set пользователя (скользящая экспирация) |
| `delete_token()`  | Удалить токен и убрать из set пользователя                    |
| `revoke_all()`    | Удалить все активные токены пользователя (logout-all)         |

### `dependencies.py`

| Символ                  | Описание                                                          |
|-------------------------|-------------------------------------------------------------------|
| `SessionTokenHeader`    | Annotated-тип для заголовка `X-Session-Token`                     |
| `authenticate_token()`  | Проверяет токен + продлевает TTL (скользящая экспирация); gateway middleware |
| `verify_session_token()`| Проверяет токен + соответствие `user_id`; FastAPI `Depends()`     |

### `rate_limit.py`

| Символ                    | Описание                                                                |
|---------------------------|-------------------------------------------------------------------------|
| `MAX_FAILURES_PER_BLOCK`  | 5 — попыток до кулдауна                                                |
| `MAX_BLOCKS`              | 3 — кулдаунов до блокировки                                            |
| `TOTAL_MAX_FAILURES`      | 15 — суммарно неудач до блокировки                                     |
| `COOLDOWN_TTL`            | `timedelta(minutes=5)`                                                  |
| `check_cooldown(phone)`   | Оставшееся время кулдауна (сек) или `None`                             |
| `get_total_failures(phone)` | Текущее число неудачных попыток                                       |
| `record_failure(phone)`   | Инкремент; возвращает `(total, cooldown_started, should_lock)`          |
| `reset(phone)`            | Сброс всех счётчиков (при успешном входе / разблокировке)               |

### `unlock_codes.py`

| Символ                          | Описание                                              |
|---------------------------------|-------------------------------------------------------|
| `CODE_LENGTH`                   | 6 цифр                                                |
| `DEFAULT_CODE_TTL`              | `timedelta(minutes=10)`                                |
| `generate_code()`               | Случайный цифровой код                                 |
| `save_unlock_code(user_id, code)` | Сохранить код с TTL                                  |
| `verify_unlock_code(user_id, code)` | Проверить и удалить код (True/False)               |
| `clear_unlock_code(user_id)`    | Удалить код (если есть)                                |

## Ошибки

| Код  | Ситуация                                        |
|------|--------------------------------------------------|
| 401  | Отсутствует `X-Session-Token`                    |
| 401  | Токен не найден / истёк                          |
| 403  | Токен не соответствует запрошенному `user_id`    |

## Использование

```python
from shared.redis_sessions.tokens import save_token, delete_token, revoke_all
from shared.redis_sessions.dependencies import authenticate_token

# Gateway middleware
session_data = await authenticate_token(token)
user_id = session_data["user_id"]

# Logout
await delete_token(token)

# Logout all
await revoke_all(user_id)
```
