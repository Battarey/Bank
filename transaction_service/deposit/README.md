# deposit/

Модуль пополнения банковского счёта.

## Файлы

| Файл       | Описание                                               |
|------------|--------------------------------------------------------|
| router.py  | `POST /accounts/{id}/deposit` — эндпоинт пополнения   |
| service.py | Бизнес-логика: блокировка строки, обновление баланса, создание записи, RabbitMQ-уведомление |

## Логика

1. `SELECT ... FOR UPDATE` на `bank_accounts` по `account_id`
2. Проверка: принадлежность пользователю, статус `open`
3. Обновление `balance += amount`
4. Создание записи `Transaction(type=deposit, direction=incoming, status=posted)`
5. Коммит → отправка уведомления `transaction_deposit`
