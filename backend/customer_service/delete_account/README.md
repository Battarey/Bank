# delete_account

Модуль удаления (soft delete) аккаунта пользователя.

## Файлы

| Файл         | Назначение                                                              |
|--------------|-------------------------------------------------------------------------|
| `service.py` | `delete_account()` — soft delete: статус, заморозка, сессии, уведомление |
| `router.py`  | FastAPI-эндпоинт `DELETE /users/delete`                                  |

## Логика `delete_account()`

1. Проверка пользователя: существует, `status != "deleted"`
2. `user.status` → `"deleted"`, `updated_at` → now
3. Каскадная заморозка всех `open`-счетов (`frozen_by=system`, reason="Удаление аккаунта")
4. Отзыв всех сессий из Redis (`revoke_all`)
5. Email-уведомление `account_deleted`
6. Аудит-лог через RabbitMQ

## Важно

- **Soft delete** — данные остаются в БД, ничего не стирается
- **Необратимо через API** — нет эндпоинта восстановления
- **Вход заблокирован** — login фильтрует по `status in (active, blocked)`, `deleted` отсекается
- **Unlock недоступен** — unlock проверяет `status == blocked`, для `deleted` — отказ

## Исключения

| Класс                        | HTTP | Описание                    |
|------------------------------|------|-----------------------------|
| `DeleteAccountNotFound`      | 404  | Пользователь не найден      |
| `DeleteAccountAlreadyDeleted`| 409  | Аккаунт уже удалён          |
```

