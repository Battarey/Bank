# Models

SQLAlchemy ORM-модели, описывающие таблицы PostgreSQL-базы `bank_core`. Все модели наследуются от общего `Base` (DeclarativeBase) и используются в `customer_service`, `auth_service` и Alembic-миграциях.

## Файловая архитектура
```
models/
├── base.py            # DeclarativeBase
├── user.py            # Таблица users
├── personal_data.py   # Таблица personal_data
├── passport.py        # Таблица passport
├── identifier.py      # Таблица identifiers
├── contact.py         # Таблица contacts
├── bank_account.py    # Таблица bank_accounts
└── transaction.py     # Таблица transactions
```

## Модели

### `User` — таблица `users`

Основная запись клиента банковского сервиса.

| Колонка      | Тип              | Ограничения             | Описание                        |
|------------- |------------------|-------------------------|---------------------------------|
| `id`         | `UUID`           | PK                      | Уникальный идентификатор        |
| `created_at` | `DateTime(tz)`   | NOT NULL                | Дата создания                   |
| `updated_at` | `DateTime(tz)`   | NOT NULL                | Дата последнего обновления      |
| `status`     | `Text`           | NOT NULL, default `pending` | Статус (`pending`, `active`)  |
| `is_verified`| `Boolean`        | NOT NULL, default `False`   | Верифицирован ли клиент       |
| `pin_hash`   | `Text`           | nullable                | bcrypt-хеш PIN-кода             |

### `PersonalData` — таблица `personal_data`

Персональные данные клиента (ФИО, дата рождения, пол).

| Колонка       | Тип          | Ограничения                         | Описание           |
|---------------|------------- |-------------------------------------|--------------------|
| `client_id`   | `UUID`       | PK, FK → `users.id` ON DELETE CASCADE | Ссылка на клиента |
| `last_name`   | `String(100)`| NOT NULL                            | Фамилия            |
| `first_name`  | `String(100)`| NOT NULL                            | Имя                |
| `middle_name` | `String(100)`| nullable                            | Отчество           |
| `birth_date`  | `Date`       | NOT NULL                            | Дата рождения      |
| `gender`      | `String(1)`  | NOT NULL, CHECK `IN ('M','F')`      | Пол                |

### `Passport` — таблица `passport`

Паспортные данные клиента.

| Колонка                | Тип          | Ограничения                         | Описание                 |
|------------------------|------------- |-------------------------------------|--------------------------|
| `client_id`            | `UUID`       | PK, FK → `users.id` ON DELETE CASCADE | Ссылка на клиента       |
| `series`               | `String(4)`  | NOT NULL                            | Серия паспорта            |
| `number`               | `String(6)`  | NOT NULL                            | Номер паспорта            |
| `division_code`        | `String(7)`  | NOT NULL                            | Код подразделения         |
| `issued_by`            | `Text`       | NOT NULL                            | Кем выдан                 |
| `issued_at`            | `Date`       | NOT NULL                            | Дата выдачи               |
| `expiration_date`      | `Date`       | NOT NULL                            | Срок действия             |
| `registration_address` | `Text`       | NOT NULL                            | Адрес регистрации         |

### `Identifier` — таблица `identifiers`

Идентификаторы налогоплательщика и социального страхования.

| Колонка     | Тип           | Ограничения                         | Описание         |
|-------------|-------------- |-------------------------------------|------------------|
| `client_id` | `UUID`        | PK, FK → `users.id` ON DELETE CASCADE | Ссылка на клиента |
| `inn`       | `String(12)`  | NOT NULL, UNIQUE                    | ИНН               |
| `snils`     | `String(11)`  | NOT NULL, UNIQUE                    | СНИЛС             |

### `Contact` — таблица `contacts`

Контактные данные клиента.

| Колонка     | Тип            | Ограничения                         | Описание          |
|-------------|--------------- |-------------------------------------|--------------------|
| `client_id` | `UUID`         | PK, FK → `users.id` ON DELETE CASCADE | Ссылка на клиента |
| `email`     | `String(255)`  | NOT NULL, UNIQUE                    | Email               |
| `phone`     | `String(20)`   | NOT NULL, UNIQUE                    | Телефон             |

### `BankAccount` — таблица `bank_accounts`

Банковский счёт клиента.

| Колонка          | Тип              | Ограничения                         | Описание              |
|------------------|------------------|-------------------------------------|-----------------------|
| `id`             | `UUID`           | PK                                  | UUID счёта            |
| `client_id`      | `UUID`           | FK → `users.id` ON DELETE CASCADE   | Владелец              |
| `account_number` | `CHAR(20)`       | NOT NULL, UNIQUE                    | 20-значный номер      |
| `type`           | `Text`           | NOT NULL                            | Тип (checking, savings, credit, deposit) |
| `currency`       | `CHAR(3)`        | NOT NULL                            | Валюта (RUB, USD, EUR) |
| `balance`        | `Numeric(18,2)`  | NOT NULL, default `0`               | Баланс                |
| `status`         | `Text`           | NOT NULL, default `open`            | Статус (open, closed, frozen) |
| `opened_at`      | `DateTime(tz)`   | NOT NULL                            | Дата открытия         |
| `closed_at`      | `DateTime(tz)`   | nullable                            | Дата закрытия         |
| `frozen_by`      | `Text`           | nullable                            | Кто заморозил (`user` / `system`) |
| `frozen_at`      | `DateTime(tz)`   | nullable                            | Дата заморозки        |
| `freeze_reason`  | `Text`           | nullable                            | Причина заморозки      |

### `Transaction` — таблица `transactions`

Запись о финансовой операции по счёту.

| Колонка              | Тип              | Ограничения                         | Описание              |
|------------------|------------------|-------------------------------------|----------------------|
| `id`             | `UUID`           | PK                                  | UUID транзакции    |
| `account_id`     | `UUID`           | FK → `bank_accounts.id`, indexed    | Счёт операции     |
| `type`           | `Text`           | NOT NULL, CHECK `IN ('deposit','withdrawal','transfer')` | Тип операции |
| `amount`         | `Numeric(18,2)`  | NOT NULL                            | Сумма              |
| `direction`      | `Text`           | NOT NULL, CHECK `IN ('incoming','outgoing')` | Направление      |
| `status`         | `Text`           | NOT NULL, CHECK `IN ('pending','posted','failed')` | Статус |
| `balance_before` | `Numeric(18,2)`  | NOT NULL                            | Баланс до          |
| `balance_after`  | `Numeric(18,2)`  | NOT NULL                            | Баланс после       |
| `related_account_id` | `UUID`       | FK → `bank_accounts.id`, nullable   | Второй счёт (перевод) |
| `external_ref`   | `Text`           | nullable                            | Внешняя ссылка     |
| `description`    | `Text`           | nullable                            | Описание            |
| `created_at`     | `DateTime(tz)`   | NOT NULL                            | Дата создания       |

## Связи

```
users (1) ──┬── (1) personal_data
             ├── (1) passport
             ├── (1) identifiers
             ├── (1) contacts
             └── (N) bank_accounts
                         └── (N) transactions
```

Все дочерние таблицы связаны через `client_id` → `users.id` с каскадным удалением (`ON DELETE CASCADE`). Транзакции связаны через `account_id` → `bank_accounts.id`.
