# Redis Onboarding

Модуль для работы с Redis Stack: хранение JSON-черновиков по шагам онбординга и onboarding-токенов, привязывающих клиента к незавершённой регистрации.

## Файловая архитектура
```
redis_onboarding/
├── client.py    # Синглтон-клиент Redis (REDIS_ONBOARDING_URL)
├── drafts.py    # CRUD для JSON-черновиков по шагам
└── tokens.py    # Onboarding-токены (save / load / delete, TTL 30 мин)
```

## Конфигурация

| Переменная             | Обязательна | Описание                                             |
|------------------------|-------------|------------------------------------------------------|
| `REDIS_ONBOARDING_URL` | Да          | URL Redis Stack (например `redis://redis_onboarding:6379`) |

Если переменная не задана, при импорте выводится `warnings.warn`, а при обращении к клиенту — ошибка.

## Ключи Redis

| Паттерн                            | Тип    | TTL     | Описание                         |
|-------------------------------------|--------|---------|----------------------------------|
| `onboarding:{user_id}:{step}`       | JSON   | 24 ч    | Черновик шага онбординга          |
| `onboarding:token:{token}`          | String | 30 мин  | Отображение onboarding-token → user_id |

## Экспорт

### `client.py`

| Символ         | Описание                                         |
|----------------|--------------------------------------------------|
| `get_client()` | Возвращает синглтон `redis.asyncio.Redis`        |
| `close_client()` | Закрывает пул соединений (вызывается при остановке) |

### `drafts.py`

| Символ          | Описание                                             |
|-----------------|------------------------------------------------------|
| `StepName`      | Literal: `personal_data`, `passport`, `identifiers`, `contacts` |
| `ALL_STEPS`     | Кортеж всех шагов                                    |
| `DraftRecord`   | TypedDict: `payload`, `status`, `updated_at`         |
| `save_draft()`  | Сохранить / перезаписать черновик шага                |
| `load_draft()`  | Получить черновик шага (или `None`)                   |
| `clear_draft()` | Удалить черновик конкретного шага                     |
| `clear_all()`   | Удалить все черновики пользователя                    |

### `tokens.py`

| Символ                      | Описание                                      |
|-----------------------------|-----------------------------------------------|
| `DEFAULT_ONBOARDING_TTL`    | `timedelta(minutes=30)`                       |
| `generate_token()`          | Генерирует `secrets.token_urlsafe(32)`        |
| `save_onboarding_token()`   | Сохранить token → user_id с TTL               |
| `load_onboarding_token()`   | Получить user_id по токену (или `None`)        |
| `delete_onboarding_token()` | Удалить токен (после finalize)                 |

## Использование

```python
from shared.redis_onboarding.drafts import save_draft, load_draft
from shared.redis_onboarding.tokens import generate_token, save_onboarding_token

# Сохранить черновик шага
await save_draft(user_id, "personal_data", {"last_name": "Иванов", ...})

# Сгенерировать и сохранить onboarding-токен
token = generate_token()
await save_onboarding_token(token, user_id)
```
