# passport

Документальные данные клиента: серия/номер паспорта, адрес регистрации. Связан с `users` по `client_id`, используется при открытии счетов.

| Column              | Type        | Constraints                               | Description                                           |
|---------------------|-------------|-------------------------------------------|-------------------------------------------------------|
| client_id           | UUID        | PK, FK -> users.id, NOT NULL              | Ссылка на владельца паспорта.                         |
| series              | CHAR(4)     | NOT NULL                                  | Серия паспорта без пробелов.                          |
| number              | CHAR(6)     | NOT NULL                                  | Номер паспорта.                                       |
| division_code       | CHAR(7)     | NOT NULL                                  | Код подразделения в формате `XXX-XXX`.                |
| issued_by           | TEXT        | NOT NULL                                  | Орган, выдавший документ.                             |
| issued_at           | DATE        | NOT NULL                                  | Дата выдачи.                                          |
| expiration_date     | DATE        | NOT NULL                                  | Дата окончания действия документа.                    |
| registration_address| TEXT        | NOT NULL                                  | Адрес регистрации из паспорта.                        |


