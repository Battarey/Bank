# withdrawal

Модуль снятия средств с банковского счёта.

## Файлы

| Файл        | Назначение                                                           |
|-------------|----------------------------------------------------------------------|
| `service.py` | `withdraw()` — блокировка строки, проверка баланса, создание записи |
| `router.py`  | `POST /accounts/{id}/withdraw`                                      |

## Логика `withdraw()`

1. `SELECT ... FOR UPDATE` на `bank_accounts` по `account_id`
2. Проверка: принадлежность пользователю, статус `open`, достаточность средств
3. Обновление `balance -= amount`
4. Создание записи `Transaction(type=withdrawal, direction=outgoing, status=posted)`
5. Коммит → отправка уведомления `transaction_withdrawal`

## Уведомления

После успешного снятия публикуется RabbitMQ-сообщение `transaction_withdrawal` с переменными `{account_number}`, `{amount}`, `{currency}`, `{balance_after}`.

## Исключения (из `transaction_service.exceptions`)

| Класс                 | HTTP | Описание                                       |
|-----------------------|------|------------------------------------------------|
| `AccountNotFound`     | 404  | Счёт не найден или не принадлежит пользователю |
| `AccountNotOpen`      | 409  | Статус ≠ `open`                                |
| `InsufficientFunds`   | 422  | Недостаточно средств на счёте                  |
| `TransactionConflict` | 409  | Конфликт данных при коммите                    |
