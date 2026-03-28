# users

Основная таблица клиентов: фиксирует факт регистрации и текущий статус профиля. Связана по внешнему ключу с большинством остальных таблиц (personal_data, passport, identifiers, contacts, bank_accounts).

| Column      | Type        | Constraints                             | Description                                                |
|-------------|-------------|-----------------------------------------|------------------------------------------------------------|
| id          | UUID        | PK, NOT NULL                            | Уникальный идентификатор клиента.                          |
| created_at  | TIMESTAMP   | NOT NULL, UTC                           | Время регистрации клиента.                                 |
| updated_at  | TIMESTAMP   | NOT NULL, UTC                           | Последнее обновление карточки клиента.                     |
| status      | TEXT        | NOT NULL, CHECK (active/blocked/deleted)| Финальный статус профиля.                                  |
| is_verified | BOOLEAN     | NOT NULL, DEFAULT FALSE                 | Флаг прохождения полной KYC-верификации.                   |
