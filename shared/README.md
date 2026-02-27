# Shared

Общий пакет с переиспользуемой логикой для всех микросервисов: ORM-модели, Pydantic-схемы, подключения к БД и Redis, внутренняя аутентификация.

## Файловая архитектура
```
shared/
├── database_core/               # Подключение к PostgreSQL (async engine, сессии)
├── internal_auth/               # Защита микросервисов от прямого доступа
├── models/                      # SQLAlchemy ORM-модели
├── redis_onboarding/            # Redis Stack — черновики и onboarding-токены
├── redis_sessions/              # Redis — сессионные токены
├── schemas/                     # Pydantic-схемы для запросов и ответов
└── README.md
```  

## Кто использует

| Подпакет           | gateway | customer | auth |
|--------------------|---------|----------|------|
| `database_core`    |         | ✓        | ✓    |
| `internal_auth`    |         | ✓        | ✓    |
| `models`           |         | ✓        | ✓    |
| `redis_onboarding` | ✓       | ✓        |      |
| `redis_sessions`   | ✓       |          | ✓    |
| `schemas`          | ✓       | ✓        | ✓    |
