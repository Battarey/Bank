# transactions

Фиксирует все операции по счетам: пополнения, снятия, переводы. Связана с `bank_accounts` через `account_id` и при переводах ссылается на счёт-контрагент через `related_account_id`.

| Column            | Type          | Constraints                                             | Description                                                     |
|-------------------|---------------|---------------------------------------------------------|-----------------------------------------------------------------|
| id                | UUID          | PK, NOT NULL                                            | Уникальный идентификатор транзакции.                            |
| account_id        | UUID          | FK -> bank_accounts.id, NOT NULL                        | Счёт, по которому проходит операция.                            |
| type              | TEXT          | NOT NULL, CHECK (deposit/withdrawal/transfer)           | Тип операции.                                                   |
| amount            | NUMERIC(18,2) | NOT NULL                                                | Сумма транзакции.                                               |
| created_at        | TIMESTAMP     | NOT NULL                                                | Когда операция была создана.                                    |
| description       | TEXT          | NULLABLE                                                | Комментарий пользователя/системы.                               |
| related_account_id| UUID          | NULLABLE, FK -> bank_accounts.id                        | Счёт-контрагент для переводов.                                  |
| direction         | TEXT          | NOT NULL, CHECK (incoming/outgoing)                     | Относительно владельца счёта.                                   |
| status            | TEXT          | NOT NULL, CHECK (pending/posted/failed)                 | Текущее состояние обработки.                                    |
| balance_before    | NUMERIC(18,2) | NOT NULL                                                | Баланс счёта до применения операции.                            |
| balance_after     | NUMERIC(18,2) | NOT NULL                                                | Баланс после выполнения.                                        |
| external_ref      | TEXT          | NULLABLE                                                | Ссылка на внешнюю систему/платёж.                               |


