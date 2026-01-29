# Backend для банковского приложения 

## Стек
 - Python: FastAPI, asyncio, Pytest, sqlalchemy, httpx
 - БД: PostgreSQL, CkickHouse, Redis, MongoDB
 - RabbitMQ

## Файловая архитектура
```
bank
├── auth_service/                # Сервис для авторизации/регистрации/деавторизации
├── bank_account_service/        # Сервис для работы с счетами пользователя
├── bd_service/                  # Сервис для работы с БД
├── currency_service/            # Сервис для работы с иностранными валютами
├── gateway_service/
├── log_service/                 # Сервис для логирования
├── metal_service/               # Сервис для работы с драг.металлами
├── notification_service/        # Сервис для уведомлений
├── transaction_service/         # Сервис для транзакций
├── .dockerignore
├── .gitignore
├── docker-compose.yaml
└── README.md
```

## TODO: 
 - Добавить описание каждому полю в tables и описание самой таблицы
 - Сформировать ER-диаграмму
 - Добавить необходимые таблицы и поля
 - Реализация Alembic для БД
 - Функционал верификации email
 - Функционал логирования
 - Функционал уведомлений
