# Customer Service

Сервис управления данными клиента: онбординг (создание аккаунта), обновление личных данных, удаление аккаунта.

## Стек
- Python: FastAPI, SQLAlchemy (asyncio), Pydantic
- БД: PostgreSQL (постоянное хранилище), Redis Stack (черновики онбординга)
- Очередь: RabbitMQ (отправка email через notification_service)
- Аутентификация: X-Internal-Key (все запросы приходят только через gateway)
- Логирование: при завершении регистрации публикуется бизнес-событие в exchange `logs` (routing key `log.auth`) для аудит-лога

## Файловая архитектура
```
customer_service/
├── create_account/              # Онбординг: создание пользователя и сбор данных
├── delete_account/              # Удаление аккаунта (в разработке)
├── update_user_data/            # Обновление личных данных активного пользователя
├── tests/                       # Тесты (в разработке)
├── main.py                      # Точка входа: lifespan (Redis + RabbitMQ), роутеры
├── Dockerfile
├── requirements.txt
└── README.md
```

## Эндпоинты

### Онбординг (create_account)

| Метод  | Путь                                       | Описание                                                |
|--------|--------------------------------------------|---------------------------------------------------------|
| POST   | `/users/start`                             | Создание пользователя (`pending`)                       |
| POST   | `/users/{user_id}/account/personal-data`   | ФИО, дата рождения, пол                                 |
| POST   | `/users/{user_id}/account/passport`        | Паспортные данные (KYC)                                 |
| POST   | `/users/{user_id}/account/identifiers`     | ИНН, СНИЛС                                              |
| POST   | `/users/{user_id}/account/contacts`        | Телефон и email                                         |
| POST   | `/users/{user_id}/account/send-email-code` | Отправить код подтверждения на email                    |
| POST   | `/users/{user_id}/account/verify-email`    | Проверить код подтверждения email                       |
| POST   | `/users/{user_id}/account/finalize`        | Перенос из Redis в PostgreSQL, `active` + welcome email |

### Обновление данных (update_user_data)

| Метод  | Путь                     | Описание                        |
|--------|--------------------------|---------------------------------|
| PATCH  | `/users/personal-data`   | Частичное обновление ФИО        |
| PUT    | `/users/passport`        | Полная замена паспортных данных |
| PATCH  | `/users/contacts`        | Частичное обновление контактов  |

> `user_id` извлекается из заголовка `X-User-ID`, проброшенного gateway.

## Email-верификация

Отправка email выполняется **асинхронно через RabbitMQ**:

```
customer_service ──(publish)──► RabbitMQ ──(consume)──► notification_service ──(SMTP)──► Gmail
```

1. `send-email-code` генерирует 6-значный код, сохраняет в Redis и публикует задачу в очередь
2. `verify-email` проверяет код (через `hmac.compare_digest`) и ставит флаг `email_verified`
3. `finalize` не выполнится без подтверждённого email
4. При успешном `finalize` отправляется приветственное письмо (шаблон `welcome`)

## Обработка ошибок

| Код  | Когда                                                       |
|------|---------------------------------------------------------|
| 400  | Ошибка валидации данных / email не подтверждён          |
| 404  | Пользователь или запись не найдены                     |
| 409  | Конфликт уникальности (ИНН, СНИЛС, телефон, email) |
| 422  | Пустой запрос (ни одно поле не передано)            |
