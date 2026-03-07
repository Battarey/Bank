# Redis Onboarding

Модуль для работы с Redis Stack: хранение JSON-черновиков по шагам онбординга и onboarding-токенов, привязывающих клиента к незавершённой регистрации.

## Файловая архитектура
```
redis_onboarding/
├── client.py       # Синглтон-клиент Redis (REDIS_ONBOARDING_URL)
├── drafts.py       # CRUD для JSON-черновиков по шагам
├── email_codes.py  # Коды подтверждения email (generate, save, verify)
└── tokens.py       # Onboarding-токены (save / load / touch / delete, TTL 15 мин, скользящая)
```

## Конфигурация

| Переменная             | Обязательна | Описание                                                   |
|------------------------|-------------|------------------------------------------------------------|
| `REDIS_ONBOARDING_URL` | Да          | URL Redis Stack (например `redis://redis_onboarding:6379`) |

Если переменная не задана, при импорте выводится `warnings.warn`, а при обращении к клиенту — ошибка.

## Ключи Redis

| Паттерн                               | Тип    | TTL     | Описание                                                       | 
|---------------------------------------|--------|---------|----------------------------------------------------------------|
| `onboarding:{user_id}:{step}`         | JSON   | 24 ч    | Черновик шага онбординга                                       |
| `onboarding:token:{token}`            | String | 15 мин  | Отображение onboarding-token → user_id (скользящая экспирация) |
| `onboarding:{user_id}:email_code`     | String | 10 мин  | 6-значный код подтверждения email                              |
| `onboarding:{user_id}:email_verified` | String | 24 ч    | Флаг подтверждения email (`"1"`)                               |    

## Экспорт

### `client.py`

| Символ           | Описание                                            |
|------------------|-----------------------------------------------------|
| `get_client()`   | Возвращает синглтон `redis.asyncio.Redis`           |
| `close_client()` | Закрывает пул соединений (вызывается при остановке) |

### `drafts.py`

| Символ          | Описание                                                        |
|-----------------|-----------------------------------------------------------------|
| `StepName`      | Literal: `personal_data`, `passport`, `identifiers`, `contacts` |
| `ALL_STEPS`     | Кортеж всех шагов                                               |
| `DraftRecord`   | TypedDict: `payload`, `status`, `updated_at`                    |
| `save_draft()`  | Сохранить / перезаписать черновик шага                          |
| `load_draft()`  | Получить черновик шага (или `None`)                             |
| `clear_draft()` | Удалить черновик конкретного шага                               |
| `clear_all()`   | Удалить все черновики пользователя                              |

### `tokens.py`

| Символ                      | Описание                                      |
|-----------------------------|-----------------------------------------------|
| `DEFAULT_ONBOARDING_TTL`    | `timedelta(minutes=15)`                       |
| `generate_token()`          | Генерирует `secrets.token_urlsafe(32)`        |
| `save_onboarding_token()`   | Сохранить token → user_id с TTL               |
| `load_onboarding_token()`   | Получить user_id по токену (или `None`)       |
| `touch_onboarding_token()`  | Продлить TTL (скользящая экспирация)          |
| `delete_onboarding_token()` | Удалить токен (после finalize)                |

### `email_codes.py`

| Символ                        | Описание                                                                            |
|-------------------------------|-------------------------------------------------------------------------------------|
| `CODE_LENGTH`                 | `6` — длина кода подтверждения                                                      |
| `DEFAULT_CODE_TTL`            | `timedelta(minutes=10)`                                                             |
| `generate_code()`             | Генерирует 6-значный цифровой код                                                   |
| `save_email_code()`           | Сохранить код с TTL 10 мин                                                          |
| `verify_email_code()`         | Проверить код (через `hmac.compare_digest`), при успехе — поставить флаг verified   |
| `is_email_verified()`         | Проверить флаг подтверждения                                                        |
| `clear_email_verification()`  | Удалить код + флаг (после finalize)                                                 |
