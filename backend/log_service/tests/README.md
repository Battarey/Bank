# Тестирование (tests)

Гарантия корректной обработки и маршрутизации логов.

## Специфика тестов
В отличие от API-сервисов, здесь основное внимание уделяется тестированию асинхронных потребителей:
- **Consumer Unit Tests**: Мокирование RabbitMQ и проверка правильности вызова методов репозитория при получении корректных и некорректных JSON-сообщений.
- **Repository Integration**: Проверка фактической записи в тестовые базы данных.

## Запуск тестов

### Локальный запуск
```powershell
pytest backend/log_service/tests
```

### Запуск через Docker
```powershell
docker compose run --rm -e APP_ENV=test log_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest log_service/tests/unit -v"
```

### Проверка схемы валидации событий
```powershell
pytest backend/log_service/tests/test_schemas.py
```

## Требования
Для тестов требуется наличие `shared` библиотеки в PYTHONPATH и установленные зависимости из `requirements-test.txt`.
