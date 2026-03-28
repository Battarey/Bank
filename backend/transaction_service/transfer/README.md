# transfer

Модуль переводов между банковскими счетами (собственные и чужие).

## Файлы

| Файл        | Назначение                                                          |
|-------------|---------------------------------------------------------------------|
| `service.py` | `transfer()` — deadlock-safe блокировка двух счетов, два перевода  |
| `router.py`  | `POST /accounts/{id}/transfer`                                     |

## Логика `transfer()`

1. Проверка: `from_id ≠ to_id` (SameAccountTransfer)
2. Блокировка обоих счетов `FOR UPDATE` в порядке `sorted([from_id, to_id])` — предотвращение deadlock
3. Проверка: владелец отправителя, оба в статусе `open`, одинаковая валюта, достаточно средств
4. Обновление балансов обоих счетов
5. Создание **двух** записей:
   - Outgoing (у отправителя): `related_account_id = to_id`
   - Incoming (у получателя): `related_account_id = from_id`
6. Коммит → уведомление отправителю (`transaction_transfer`)
7. Если получатель — другой клиент → уведомление получателю (`transaction_incoming`)

## Уведомления

- Отправитель: `transaction_transfer` с переменными `{from_account}`, `{to_account}`, `{amount}`, `{currency}`, `{balance_after}`
- Получатель (другой клиент): `transaction_incoming` с переменными `{account_number}`, `{from_account}`, `{amount}`, `{currency}`, `{balance_after}`

## Исключения (из `transaction_service.exceptions`)

| Класс                 | HTTP | Описание                                       |
|-----------------------|------|------------------------------------------------|
| `AccountNotFound`     | 404  | Счёт не найден или не принадлежит пользователю |
| `AccountNotOpen`      | 409  | Один из счетов не в статусе `open`             |
| `SameAccountTransfer` | 409  | Перевод на тот же счёт                         |
| `CurrencyMismatch`    | 422  | Валюты счетов не совпадают                     |
| `InsufficientFunds`   | 422  | Недостаточно средств на счёте-отправителе      |
| `TransactionConflict` | 409  | Конфликт данных при коммите                    |
