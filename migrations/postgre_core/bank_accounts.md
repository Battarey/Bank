# bank_accounts

Регистр всех счетов пользователей. Связан с `users` (владелец) и `transactions` (операции по счёту).

| Column        | Type         | Constraints                                           | Description                                         |
|---------------|--------------|-------------------------------------------------------|-----------------------------------------------------|
| id            | UUID         | PK, NOT NULL                                          | Уникальный идентификатор счета.                     |
| client_id     | UUID         | FK -> users.id, NOT NULL                              | Владелец счета.                                     |
| account_number| CHAR(20)     | UNIQUE, NOT NULL                                      | Банковский номер счёта в формате 20 цифр.           |
| type          | TEXT         | NOT NULL, CHECK (checking/savings/credit/deposit)     | Тип счета.                                          |
| currency      | CHAR(3)      | NOT NULL, CHECK (RUB/USD/EUR)                         | Основная валюта.                                    |
| balance       | NUMERIC(18,2)| NOT NULL, DEFAULT 0                                   | Текущий баланс.                                     |
| status        | TEXT         | NOT NULL, CHECK (open/closed/frozen)                  | Состояние счета.                                    |
| opened_at     | TIMESTAMP    | NOT NULL                                              | Дата/время открытия.                                |
| closed_at     | TIMESTAMP    | NULLABLE                                              | Заполняется при закрытии.                           |
