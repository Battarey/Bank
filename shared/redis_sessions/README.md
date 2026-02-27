# Redis Sessions

Модуль для работы с сессионными токенами в Redis: CRUD токенов, множества активных сессий пользователя, FastAPI-зависимости для аутентификации.

## Файловая архитектура
```
redis_sessions/
├── client.py         # Синглтон-клиент Redis (REDIS_SESSIONS_URL)
├── tokens.py         # CRUD для сессионных токенов (save / load / delete / revoke_all)
└── dependencies.py   # authenticate_token(), verify_session_token()
```

## Конфигурация

| Переменная           | Обязательна | Описание                                          |
|----------------------|-------------|----------------------------------------------------|
| `REDIS_SESSIONS_URL` | Да          | URL Redis (например `redis://redis_sessions:6379`) |

Если переменная не задана, при импорте выводится `warnings.warn`, а при обращении к клиенту — ошибка.

## Ключи Redis

| Паттерн                    | Тип   | TTL    | Описание                                  |
|-----------------------------|-------|--------|--------------------------------------------|
| `session:token:{token}`     | Hash  | 30 мин | Данные сессии (`user_id` + payload)        |
| `session:user:{user_id}`    | Set   | 30 мин | Множество активных токенов пользователя    |

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
| `delete_token()`  | Удалить токен и убрать из set пользователя                    |
| `revoke_all()`    | Удалить все активные токены пользователя (logout-all)         |

### `dependencies.py`

| Символ                  | Описание                                                          |
|-------------------------|-------------------------------------------------------------------|
| `SessionTokenHeader`    | Annotated-тип для заголовка `X-Session-Token`                     |
| `authenticate_token()`  | Проверяет наличие и валидность токена; используется в gateway middleware |
| `verify_session_token()`| Проверяет токен + соответствие `user_id`; FastAPI `Depends()`     |

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
