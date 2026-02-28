# Shared

Общий пакет с переиспользуемой логикой для всех микросервисов: ORM-модели, Pydantic-схемы, подключения к БД и Redis, RabbitMQ-клиент, внутренняя аутентификация.

## Файловая архитектура
```
shared/
├── database_core/               # Подключение к PostgreSQL (async engine, сессии)
├── internal_auth/               # Защита микросервисов от прямого доступа (timing-safe)
├── models/                      # SQLAlchemy ORM-модели
├── rabbitmq/                    # RabbitMQ-клиент (aio-pika): publish, connect
├── redis_onboarding/            # Redis Stack — черновики, onboarding-токены, email-коды
├── redis_sessions/              # Redis — сессионные токены
├── schemas/                     # Pydantic-схемы для запросов и ответов
├── utils/                       # Утилиты нормализации данных (normalize_name, normalize_email и др.)
└── README.md
```  

## Кто использует

| Подпакет           | gateway | customer | auth | notification |
|--------------------|---------|----------|------|--------------|
| `database_core`    |         | ✓        | ✓    |              |
| `internal_auth`    |         | ✓        | ✓    |              |
| `models`           |         | ✓        | ✓    |              |
| `rabbitmq`         |         | ✓        | ✓    |              |
| `redis_onboarding` | ✓       | ✓        |      |              |
| `redis_sessions`   | ✓       |          | ✓    |              |
| `schemas`          | ✓       | ✓        | ✓    |              |
| `utils`            |         | ✓        |      |              |
