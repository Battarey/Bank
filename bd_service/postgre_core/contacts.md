# contacts

Таблица для контактной информации (email и телефон), необходимой для уведомлений и подтверждений. Связана с `users` через `client_id`.

| Column    | Type         | Constraints                          | Description                                   |
|-----------|--------------|--------------------------------------|-----------------------------------------------|
| client_id | UUID         | PK, FK -> users.id, NOT NULL         | Ссылка на клиента.                            |
| email     | VARCHAR(255) | UNIQUE, NOT NULL                     | Почта в нижнем регистре.                      |
| phone     | VARCHAR(20)  | UNIQUE, NOT NULL                     | Телефон в формате E.164.                      |

