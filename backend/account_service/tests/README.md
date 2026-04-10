# Тестирование (tests)

Инфраструктура тестов для обеспечения качества логики управления счетами.

## Структура тестов
- `/unit`: Изолированные тесты бизнес-логики (`service.py`) и эндпоинтов (`router.py`) с использованием моков БД и RabbitMQ.

## Запуск тестов
```powershell
docker compose run --rm -e APP_ENV=test account_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest account_service/tests/unit -v"
```
