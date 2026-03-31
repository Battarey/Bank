# Тестирование (tests)

Инфраструктура тестов для обеспечения качества логики управления счетами.

## Структура тестов
- `/unit`: Изолированные тесты бизнес-логики (`service.py`) и эндпоинтов (`router.py`) с использованием моков БД и RabbitMQ.
- `/integration`: Комплексные тесты взаимодействия с реальной базой данных и Unit of Work.

## Запуск тестов

### 1. Запуск всех тестов сервиса
```powershell
pytest backend/account_service/tests
```

### 2. Запуск только Unit-тестов
```powershell
pytest backend/account_service/tests/unit
```

### 3. Запуск конкретного модуля (например, открытия счетов)
```powershell
pytest backend/account_service/tests/unit/test_open_account_service.py
```

## Требования
Все тесты используют асинхронный движок `pytest-asyncio`. Конфигурация фикстур (UoW, БД, моки) находится в файлах `conftest.py` в соответствующих папках.