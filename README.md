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
 - Прописать значения для БД в docker-compose
 - Добавить описание каждому полю в tables и описание самой таблицы
 - Реализация Alembic для БД
 


