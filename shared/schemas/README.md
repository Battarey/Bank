# Schemas

Pydantic-схемы для валидации запросов и формирования ответов. Используются всеми микросервисами через `shared.schemas`.

## Файловая архитектура
```
schemas/
├── auth.py                # Аутентификация: логин по PIN, установка PIN
├── onboarding.py          # Онбординг: Start / Finalize (internal + gateway)
├── personal_data.py       # ФИО, дата рождения, пол
├── passport.py            # Паспортные данные
├── identifiers.py         # ИНН, СНИЛС
├── contacts.py            # Email, телефон
├── email_verification.py  # Коды подтверждения email
├── unlock.py              # Разблокировка аккаунта
└── bank_account.py        # Банковские счета: открытие, закрытие, список
```

## Схемы по файлам

### `auth.py`

| Схема              | Тип     | Поля                        | Описание                      |
|--------------------|---------|-----------------------------|-----------  --------------------|
| `LoginPinRequest`  | Request | `phone` (Phone), `pin` (Pin) | Запрос логина по PIN          |
| `LoginPinResponse` | Response| `session_token`, `user_id`   | Ответ с сессионным токеном    |
| `SetPinRequest`    | Request | `pin` (Pin)                  | Установка / смена PIN         |
| `MessageResponse`  | Response| `message`                    | Универсальный текстовый ответ |

**Типы:**
- `Phone` — `str`, паттерн `^\+7\d{10}$`
- `Pin` — `str`, паттерн `^\d{4,6}$`

### `onboarding.py`

| Схема                     | Используется   | Поля                              | Описание                          |
|---------------------------|----------------|-----------------------------------|------------------------------------|
| `StartInternalResponse`   | customer_service | `user_id`, `status="pending"`    | Внутренний ответ на `/start`       |
| `StartOnboardingResponse` | gateway         | `onboarding_token`, `status`     | Ответ клиенту (токен вместо user_id) |
| `FinalizeInternalResponse`| customer_service | `status="completed"`, `message`  | Внутренний ответ на `/finalize`    |
| `FinalizeResponse`        | gateway         | + `session_token`, `user_id`     | Ответ клиенту (с сессией)          |

### `personal_data.py`

| Схема                | Тип     | Описание                                        |
|----------------------|---------|-------------------------------------------------|
| `PersonalDataPayload`| Request | ФИО, `birth_date`, `gender` (M/F). `extra="forbid"` |
| `PersonalDataResponse`| Response| + `client_id`. `from_attributes=True`           |
| `PersonalDataUpdate` | Request | Частичное обновление ФИО (`birth_date` и `gender` неизменяемы) |

### `passport.py`

| Схема             | Тип      | Описание                                                      |
|-------------------|----------|----------------------------------------------------------------|
| `PassportPayload` | Request  | Серия, номер, код подразделения, кем выдан, даты, адрес. Валидатор: `expiration_date > issued_at` |
| `PassportResponse`| Response | + `client_id`. `from_attributes=True`                         |

### `identifiers.py`

| Схема                | Тип      | Описание                                  |
|----------------------|----------|-------------------------------------------|
| `IdentifiersPayload` | Request  | `inn` (12 цифр), `snils` (11 цифр)       |
| `IdentifiersResponse`| Response | + `client_id`. `from_attributes=True`     |

### `contacts.py`

| Схема             | Тип      | Описание                                                |
|-------------------|----------|---------------------------------------------------------|
| `ContactsPayload` | Request  | `email` (EmailStr), `phone` (`^\+7\d{10}$`)    |
| `ContactsResponse`| Response | + `client_id`. `from_attributes=True`                   |
| `ContactsUpdate`  | Request  | Частичное обновление email и/или phone                   |

## Паттерн Internal / Gateway

Для `/start` и `/finalize` используется разделение на две схемы:

```
customer_service             gateway_service
────────────────             ───────────────
StartInternalResponse   →    StartOnboardingResponse
FinalizeInternalResponse →   FinalizeResponse
```

`customer_service` возвращает внутреннюю схему (с `user_id`), а `gateway` оборачивает её в публичную (с токенами).

### `email_verification.py`

| Схема                    | Тип      | Поля                                           | Описание                             |
|--------------------------|----------|------------------------------------------------|------------------------------------------|
| `SendEmailCodeRequest`   | Request  | `email` (EmailStr)                             | Запрос на отправку кода подтверждения |
| `VerifyEmailCodeRequest` | Request  | `code` (6 цифр, `^\d{6}$`)                    | Запрос на проверку кода               |
| `EmailCodeResponse`      | Response | `message`, `email_verified` (bool)             | Ответ на отправку / проверку кода   |

### `unlock.py`

| Схема                    | Тип      | Поля                                | Описание                                |
|--------------------------|----------|--------------------------------------|--------------------------------------------|
| `RequestUnlockRequest`   | Request  | `email` (EmailStr)                   | Запрос на отправку кода разблокировки |
| `UnlockRequest`          | Request  | `email` (EmailStr), `code` (`^\d{6}$`) | Проверка кода и разблокировка         |

### `bank_account.py`

**Типы:**
- `AccountType` — `Literal["checking", "savings", "credit", "deposit"]`
- `Currency` — `Literal["RUB", "USD", "EUR"]`
- `AccountStatus` — `Literal["open", "closed", "frozen"]`

| Схема                    | Тип      | Поля                                           | Описание                              |
|--------------------------|----------|------------------------------------------------|---------------------------------------|
| `OpenAccountRequest`     | Request  | `type` (AccountType), `currency` (Currency)    | Запрос на открытие счёта              |
| `CloseAccountRequest`    | Request  | (пустое тело, `extra="forbid"`)                | ID счёта из пути                      |
| `AccountResponse`        | Response | `id`, `client_id`, `account_number`, `type`, `currency`, `balance`, `status`, `opened_at`, `closed_at` | Полные данные счёта |
| `AccountListResponse`    | Response | `accounts` (list[AccountResponse]), `total`    | Список счетов пользователя            |
| `AccountMessageResponse` | Response | `message`, `account` (AccountResponse)         | Результат операции со счётом          |
