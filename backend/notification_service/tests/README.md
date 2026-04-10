# Тестирование (tests)

Проверка корректности формирования писем и интеграции с почтовыми сервисами.

## Структура тестов
- `/unit`: Тестирование рендеринга шаблонов. Проверяется, что все плэйсхолдеры корректно заменяются данными и не вызывают ошибок при отсутствии переменной.

## Запуск тестов
```powershell
docker compose run --rm -e APP_ENV=test notification_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest notification_service/tests/unit -v"
```
