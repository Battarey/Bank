# Database Core

Ядро для работы с данными, реализующее паттерны **Unit of Work** и **Repository/Query**. Обеспечивает асинхронное подключение к PostgreSQL через SQLAlchemy 2.0.

## Файловая архитектура
```
database_core/
├── db.py                     # Подключение, движок и фабрика сессий
├── uow.py                    # Паттерн Unit of Work (Abstract & SqlAlchemy)
├── base_repository.py         # Базовый ORM-репозиторий (Write)
├── base_query_repository.py   # Базовый Query-репозиторий (Read/CQRS)
└── env.py                    # Настройки окружения
```

## Основные компоненты

### 1. Unit of Work (`uow.py`)
Управляет жизненным циклом сессии и атомарностью операций.
- **`AbstractUnitOfWork`**: Интерфейс с поддержкой `commit`, `rollback` и очереди событий.
- **`SqlAlchemyUnitOfWork`**: Реализация для SQLAlchemy. Автоматически закрывает сессию и публикует доменные события после коммита.

### 2. Repository (`base_repository.py`)
Инкапсулирует логику работы с сущностями через ORM.
- Методы: `get`, `list`, `add`, `add_all`, `delete`, `delete_older_than`.
- Скрывает использование `select`, `delete` и других конструкций SQLAlchemy.

### 3. Query Layer (`base_query_repository.py`)
Используется для **CQRS (Read Model)**.
- Выполняет высокопроизводительные сырые SQL-запросы (`text()`).
- Возвращает Pydantic-схемы вместо ORM-моделей.
- Идеально для сложных отчетов и агрегации данных.

## Пример использования (Service Layer)

```python
async def transfer_money(uow: AbstractUnitOfWork, ...):
    async with uow:
        sender = await uow.accounts.get(sender_id)
        receiver = await uow.accounts.get(receiver_id)
        
        # ... логика перевода ...
        
        uow.add_event(TransactionEvent(...))
        await uow.commit() # Фиксация БД + Отправка события в RabbitMQ
```
