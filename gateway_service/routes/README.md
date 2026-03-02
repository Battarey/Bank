# Маршруты Gateway

Прокси-маршруты, пересылающие запросы клиента во внутренние микросервисы.

## Файловая архитектура
```
routes/
├── account.py                   # Банковские счета (открытие, просмотр, закрытие)
├── auth.py                      # Аутентификация (login, set-pin, logout, unlock)
├── customer.py                  # Онбординг + обновление данных пользователя
├── transaction.py               # Операции по счетам (пополнение, снятие, перевод, история)
└── README.md
```

## Эндпоинты

### Онбординг (`customer.py`)

| Метод  | Путь                              | Авторизация          | Описание                                  |
|--------|-----------------------------------|----------------------|-------------------------------------------|
| POST   | `/users/start`                    | —                    | Начало онбординга, выдача onboarding-токена |
| POST   | `/users/me/account/personal-data` | `X-Onboarding-Token` | Отправка ФИО, даты рождения, пола         |
| POST   | `/users/me/account/passport`      | `X-Onboarding-Token` | Отправка паспортных данных                |
| POST   | `/users/me/account/identifiers`   | `X-Onboarding-Token` | Отправка ИНН, СНИЛС                      |
| POST   | `/users/me/account/contacts`      | `X-Onboarding-Token` | Отправка телефона и email                 |
| POST   | `/users/me/account/finalize`      | `X-Onboarding-Token` | Завершение онбординга, выдача session-токена |

### Обновление данных (`customer.py`)

| Метод  | Путь                       | Авторизация       | Описание                        |
|--------|----------------------------|--------------------|---------------------------------|
| PATCH  | `/users/me/personal-data`  | `X-Session-Token`  | Частичное обновление ФИО и т.д. |
| PUT    | `/users/me/passport`       | `X-Session-Token`  | Полная замена паспортных данных  |
| PATCH  | `/users/me/contacts`       | `X-Session-Token`  | Частичное обновление контактов  |

### Аутентификация (`auth.py`)

| Метод  | Путь                      | Авторизация       | Описание                                  |
|--------|---------------------------|--------------------|-------------------------------------------|
| POST   | `/auth/login-pin`         | —                  | Вход по телефону + PIN → session-токен    |
| POST   | `/auth/request-unlock`    | —                  | Запрос кода разблокировки на email        |
| POST   | `/auth/unlock`            | —                  | Разблокировка аккаунта по коду            |
| POST   | `/auth/set-pin`           | `X-Session-Token`  | Установка / смена PIN-кода               |
| POST   | `/auth/logout`            | `X-Session-Token`  | Выход (удаление текущей сессии)          |
| POST   | `/auth/logout-all`        | `X-Session-Token`  | Выход со всех устройств                  |

### Банковские счета (`account.py`)

| Метод  | Путь                       | Авторизация       | Описание                                |
|--------|----------------------------|--------------------|-----------------------------------------|
| POST   | `/accounts`                | `X-Session-Token`  | Открыть новый счёт                      |
| GET    | `/accounts`                | `X-Session-Token`  | Список счетов текущего пользователя     |
| GET    | `/accounts/{id}`           | `X-Session-Token`  | Детали конкретного счёта                |
| POST   | `/accounts/{id}/close`     | `X-Session-Token`  | Закрыть счёт (баланс должен быть 0)    |

### Операции по счетам (`transaction.py`)

| Метод  | Путь                              | Авторизация       | Описание                                    |
|--------|-----------------------------------|--------------------|---------------------------------------------|
| POST   | `/accounts/{id}/deposit`          | `X-Session-Token`  | Пополнить счёт                              |
| POST   | `/accounts/{id}/withdraw`         | `X-Session-Token`  | Снять со счёта                              |
| POST   | `/accounts/{id}/transfer`         | `X-Session-Token`  | Перевести между счетами (свой или чужой)    |
| GET    | `/accounts/{id}/transactions`     | `X-Session-Token`  | История операций (пагинация + фильтры)      |