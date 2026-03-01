# withdrawal/

Модуль снятия средств с банковского счёта.

## Файлы

| Файл       | Описание                                                 |
|------------|----------------------------------------------------------|
| router.py  | `POST /accounts/{id}/withdraw` — эндпоинт снятия        |
| service.py | Бизнес-логика: блокировка строки, проверка баланса, создание записи, RabbitMQ-уведомление |

## Логика

1. `SELECT ... FOR UPDATE` на `bank_accounts` по `account_id`
2. Проверка: принадлежность пользователю, статус `open`, достаточность средств
3. Обновление `balance -= amount`
4. Создание записи `Transaction(type=withdrawal, direction=outgoing, status=posted)`
5. Коммит → отправка уведомления `transaction_withdrawal`
