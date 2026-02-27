# Маршруты Gateway

Прокси-маршруты, пересылающие запросы клиента во внутренние микросервисы.

## Файловая архитектура
```
routes/
├── auth.py                      # Аутентификация (login, set-pin, logout)
├── customer.py                  # Онбординг + обновление данных пользователя
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

| Метод  | Путь               | Авторизация       | Описание                                  |
|--------|--------------------|--------------------|-------------------------------------------|
| POST   | `/auth/login-pin`  | —                  | Вход по телефону + PIN → session-токен    |
| POST   | `/auth/set-pin`    | `X-Session-Token`  | Установка / смена PIN-кода               |
| POST   | `/auth/logout`     | `X-Session-Token`  | Выход (удаление текущей сессии)          |
| POST   | `/auth/logout-all` | `X-Session-Token`  | Выход со всех устройств                  |