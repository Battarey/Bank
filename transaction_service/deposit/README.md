# deposit

Модуль пополнения банковского счёта.

## Файлы

| Файл       | Назначение                                             |
|------------|--------------------------------------------------------|
| `service.py` | `deposit()` — блокировка строки, обновление баланса, создание записи |
| `router.py`  | `POST /accounts/{id}/deposit`                        |

## Логика `deposit()`

1. `SELECT ... FOR UPDATE` на `bank_accounts` по `account_id`
2. Проверка: принадлежность пользователю, статус `open`
3. Обновление `balance += amount`
4. Создание записи `Transaction(type=deposit, direction=incoming, status=posted)`
5. Коммит → отправка уведомления `transaction_deposit`

## Уведомления

После успешного пополнения публикуется RabbitMQ-сообщение `transaction_deposit` с переменными `{account_number}`, `{amount}`, `{currency}`, `{balance_after}`.

## Исключения (из `transaction_service.exceptions`)

| Класс                 | HTTP | Описание                                       |
|-----------------------|------|-------------------------------------------------|
| `AccountNotFound`     | 404  | Счёт не найден или не принадлежит пользователю |
| `AccountNotOpen`      | 409  | Статус ≠ `open`                                |
| `TransactionConflict` | 409  | Конфликт данных при коммите                    |
