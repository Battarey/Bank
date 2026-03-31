# Shared Library (Общий Пакет)

Централизованный пакет для всего переиспользуемого кода между микросервисами банковского бэкенда. Гарантирует единообразие архитектуры, моделей данных и протоколов взаимодействия.

## Файловая архитектура
```
shared/
├── database_core/      # UoW, BaseRepository, BaseQueryRepository
├── rabbitmq/           # MessageBus, RMQ Client, Domain Events
├── redis_sessions/     # Хранилище сессий (Auth)
├── redis_onboarding/   # Черновики KYC (Customer)
├── schemas/            # Общие Pydantic модели
├── utils/              # Глобальные исключения и нормализаторы
└── internal_auth/      # Логика X-Internal-Key
```

## Архитектурное ядро (database_core)

Базовые абстракции для реализации 4-слойной структуры:
-   **`AbstractUnitOfWork`**: Интерфейс для управления транзакциями БД и очередью доменных событий. 
-   **`SqlAlchemyUnitOfWork`**: Стандартная реализация UoW на базе SQLAlchemy 2.0.
-   **`BaseRepository`**: Базовый CRUD-слой для ORM-моделей.
-   **`BaseQueryRepository`**: Слой для высокопроизводительных сырых SQL-запросов (CQRS Read Model).

## Событийная модель (events & rabbitmq)

Реализация **EDA (Event-Driven Architecture)**:
-   **`BaseEvent`**: Базовый класс для всех доменных событий.
-   **`NotificationEvent`**: Событие для отправки Email.
-   **`LogEvent`**: Событие для аудита и аналитики.
-   **`MessageBus`**: Отвечает за трансляцию событий из UoW в RabbitMQ.
-   **`rabbitmq/helpers`**: Обертки для безопасной публикации сообщений.

## Модели и схемы (models & schemas)

-   **`models`**: SQLAlchemy-сущности (User, BankAccount, Transaction и др.). Единый источник истины для структуры БД.
-   **`schemas`**: Pydantic-модели для валидации запросов и ответов. Разделены по доменным областям (auth, bank, customer и т.д.).

## Безопасность и хранилища

-   **`internal_auth`**: Проверка заголовка `X-Internal-Key` (Timing-safe comparison).
-   **`redis_sessions`**: Пул соединений для управления сессиями.
-   **`redis_onboarding`**: Пул соединений для черновиков регистрации.
-   **`history_core` & `clickhouse_core`**: Клиенты для работы с аудит-логом (PostgreSQL) и аналитикой (ClickHouse).

## Утилиты (utils)

-   **`exceptions_handler`**: Глобальный обработчик ошибок для микросервисов.
-   **`exceptions`**: Иерархия бизнес-исключений `BaseBusinessError`.
-   **`normalize`**: Функции нормализации телефонов, имен и Email.

---

## Установка и использование

Этот пакет устанавливается во всех микросервисах через `Dockerfile` путем копирования директории `shared/` во внутреннюю структуру Python-пакетов.

**Правила импорта**:
```python
from shared.database_core.uow import AbstractUnitOfWork
from shared import schemas, models
```
