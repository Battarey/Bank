# Customer Service

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791.svg)
![Redis](https://img.shields.io/badge/Redis-Stack-D82C20.svg)

Центральный сервис управления данными клиентов: онбординг, ведение досье, обновление персональной информации и мягкое удаление.

## Архитектура

Сервис построен по принципам **Layered Architecture** и строго следует 4-х слойной структуре (api, services, repositories, core).

```text
customer_service/
├── api/                # Слой Routers: онбординг, обновление данных, удаление
├── services/           # Слой Services: бизнес-логика регистрации и управления данными
├── repositories/       # Слой Repository: работа с БД (ORM + SQL/CQRS)
├── core/               # Инфраструктурный слой: uow, exceptions
├── main.py             # Точка входа в приложение
└── README.md
```

## Безопасность данных

-   **Encryption**: Все чувствительные данные (PII: ФИО, Паспорт, Контакты) шифруются перед сохранением в PostgreSQL с использованием асимметричного шифрования.
-   **Redis Stack**: JSON-черновики онбординга хранятся в защищенном инстансе Redis с ограниченным TTL.
-   **Decryption**: Расшифровка происходит "на лету" в сервисном слое и в CQRS-слое для чтения.

## Бизнес-правила

-   **Уникальность**: ИНН, СНИЛС, Email и номер телефона должны быть уникальными во всей системе.
-   **Иммутабельность**: Дата рождения и пол устанавливаются один раз при регистрации и не подлежат изменению через стандартные методы.
-   **Статусность**: Только активные (`active`) пользователи могут совершать финансовые операции.

## API Спецификация

Все внутренние запросы требуют заголовок `X-Internal-Key`.

| Метод | Путь                               | Описание                                  | Заголовки |
|-------|------------------------------------|-------------------------------------------|-----------|
| POST  | `/onboarding`                      | Начало регистрации (создание черновика)   | -         |
| POST  | `/onboarding/{id}/personal-data`   | Шаг 1: ФИО и дата рождения                | -         |
| POST  | `/onboarding/{id}/passport`        | Шаг 2: Паспортные данные                  | -         |
| POST  | `/onboarding/{id}/identifiers`     | Шаг 3: ИНН и СНИЛС                        | -         |
| POST  | `/onboarding/{id}/contacts`        | Шаг 4: Email и Телефон                    | -         |
| POST  | `/onboarding/{id}/email/send`      | Запрос кода подтверждения на Email        | -         |
| POST  | `/onboarding/{id}/email/verify`    | Проверка кода Email                       | -         |
| POST  | `/onboarding/{id}/completion`      | Финализация и активация профиля           | -         |
| GET   | `/users/me`                        | Получить полный профиль                   | `X-User-ID` |
| PATCH | `/users/personal-data`             | Обновить ФИО                              | `X-User-ID` |
| PUT   | `/users/passport`                  | Смена паспорта                            | `X-User-ID` |
| PATCH | `/users/contacts`                  | Обновить Email/Телефон                    | `X-User-ID` |
| DELETE| `/users/me`                        | Удалить аккаунт (Soft Delete)             | `X-User-ID` |
| GET   | `/health`                          | Проверка состояния сервиса                | -         |

## Доменные события (Domain Events)

| Событие              | Получатель (Exchange) | Описание                                   |
|----------------------|-----------------------|--------------------------------------------|
| `email_verification` | `notifications`       | Отправка кода подтверждения регистрации    |
| `welcome`            | `notifications`       | Приветственное письмо после активации      |
| `registration`       | `logs`                | Запись о завершении регистрации            |
| `update_personal_data` | `logs`              | Лог изменения ФИО                          |
| `replace_passport`   | `logs`                | Лог смены паспортных данных                |
| `update_contacts`    | `logs`                | Лог изменения контактов                    |

## Переменные окружения

| Ключ | Описание | Значение по умолчанию |
|------|----------|-----------------------|
| `APP_ENV` | Окружение (local, test, dev, prod) | `local` |
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgresql+asyncpg://...` |
| `REDIS_ONBOARDING_URL` | URL для черновиков регистрации | `redis://localhost:6379/1` |
| `ENCRYPTION_KEY` | Ключ для PII-шифрования | - |
| `INTERNAL_API_KEY` | Секретный ключ для межсервисных вызовов | - |

## Технологии
- **FastAPI**: API Framework.
- **PostgreSQL**: Постоянное хранилище профилей.
- **Redis Stack**: Хранилище временных данных онбординга.
- **PyCryptodome**: Шифрование персональных данных.
- **RabbitMQ**: Публикация событий (Domain Events).
