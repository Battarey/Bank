# Заморозка и разморозка счёта

## Назначение

Заморозка (freeze) и разморозка (unfreeze) банковского счёта по инициативе пользователя или системы безопасности.

## Файловая архитектура
```
freeze_account/
├── __init__.py
├── router.py        # Эндпоинты freeze / unfreeze
├── service.py       # Бизнес-логика заморозки, каскадные операции
└── README.md
```

## Логика

### `freeze_account()`
1. Проверяет принадлежность и статус счёта (`open`).
2. Переводит `status → frozen`, сохраняет `frozen_by`, `frozen_at`, `freeze_reason`.
3. Отправляет email-уведомление `account_frozen`.

### `unfreeze_account()`
1. Проверяет, что счёт в статусе `frozen`.
2. Проверяет, что `frozen_by = "user"` (системную заморозку снять нельзя).
3. Переводит `status → open`, очищает frozen-поля.
4. Отправляет email-уведомление `account_unfrozen`.

### `cascade_freeze()`
Замораживает все `open`-счета пользователя при блокировке аккаунта (`frozen_by = "system"`).

### `cascade_unfreeze()`
Размораживает только `frozen_by = "system"` при разблокировке аккаунта. Пользовательские заморозки остаются.

## Уведомления
- `account_frozen` — при заморозке (user или system).
- `account_unfrozen` — при разморозке.

## Исключения
- `AccountNotFound` → 404
- `AccountAlreadyFrozen` → 409
- `AccountNotFrozen` → 409
- `AccountNotOpen` → 409
- `UnfreezeNotAllowed` → 403 (системная заморозка)
