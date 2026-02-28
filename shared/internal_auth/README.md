# Internal Auth

Зависимости FastAPI для защиты внутренних микросервисов от прямого доступа извне. Все запросы к `customer_service` и `auth_service` обязаны проходить через `gateway_service`, который добавляет служебные заголовки.

> Сравнение ключа выполняется через `secrets.compare_digest()` для защиты от timing-атак.

## Файловая архитектура
```
internal_auth/
└── dependencies.py    # verify_internal_key(), require_user_id()
```

## Конфигурация

| Переменная         | Обязательна | Описание                                     |
|--------------------|-------------|----------------------------------------------|
| `INTERNAL_API_KEY` | Да          | Общий секрет, одинаковый у gateway и сервисов |

## Экспорт

| Функция              | Заголовок        | Возвращает | Описание                                       |
|----------------------|------------------|------------|-------------------------------------------------|
| `verify_internal_key`| `X-Internal-Key` | `None`     | Проверяет, что запрос пришёл от gateway          |
| `require_user_id`    | `X-User-ID`      | `UUID`     | Извлекает и валидирует идентификатор пользователя |

## Ошибки

| Код  | Ситуация                              |
|------|---------------------------------------|
| 503  | `INTERNAL_API_KEY` не задан в env     |
| 403  | Неверный `X-Internal-Key`             |
| 401  | Отсутствует / невалиден `X-User-ID`   |

## Использование

```python
from shared.internal_auth import verify_internal_key, require_user_id
from fastapi import Depends

@router.post("/protected", dependencies=[Depends(verify_internal_key)])
async def protected(user_id: UUID = Depends(require_user_id)):
    ...
```
