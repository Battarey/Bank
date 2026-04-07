# Тестирование (tests)

Проверка корректности формирования писем и интеграции с почтовыми сервисами.

## Структура тестов
- `/unit`: Тестирование рендеринга шаблонов. Проверяется, что все плэйсхолдеры корректно заменяются данными и не вызывают ошибок при отсутствии переменной.
- `/integration`: Тестирование отправки с использованием мока SMTP-сервера. Проверяется корректность установки заголовков и MIME-структуры.

## Запуск тестов

### Локальный запуск
```powershell
pytest backend/notification_service/tests
```

### Запуск через Docker
```powershell
docker compose run --rm -e APP_ENV=test notification_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest notification_service/tests/unit -v"
```

### Тестирование рендеринга шаблонов
```powershell
pytest backend/notification_service/tests/unit/test_templates.py
```

## Требования
Для тестов не требуется реальный SMTP-сервер, так как используется подмена (Mock), однако RabbitMQ должен быть доступен для интеграционных сценариев.