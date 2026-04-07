# Тестирование (tests)

Инфраструктура тестов для обеспечения качества логики управления счетами.

## Структура тестов
- `/unit`: Изолированные тесты бизнес-логики (`service.py`) и эндпоинтов (`router.py`) с использованием моков БД и RabbitMQ.

## Запуск тестов

### Локальный запуск
```powershell
pytest backend/account_service/tests
```

### Запуск через Docker
```powershell
docker compose run --rm -e APP_ENV=test account_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest account_service/tests/unit -v"
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