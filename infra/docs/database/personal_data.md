# personal_data

Хранит персональные данные (ФИО, дата рождения, пол) для KYC-проверок. Один-к-одному связан с `users` через `client_id`.

| Column      | Type        | Constraints                           | Description                                      |
|-------------|-------------|---------------------------------------|--------------------------------------------------|
| client_id   | UUID        | PK, FK -> users.id, NOT NULL          | Ссылка на клиента.                               |
| last_name   | VARCHAR(100)| NOT NULL                              | Фамилия, хранится в верхнем регистре.            |
| first_name  | VARCHAR(100)| NOT NULL                              | Имя клиента.                                     |
| middle_name | VARCHAR(100)| NULLABLE                              | Отчество, если есть.                             |
| birth_date  | DATE        | NOT NULL                              | Дата рождения.                                   |
| gender      | CHAR(1)     | NOT NULL, CHECK (M/F)                 | Биологический пол, используется для отчётности.  |
