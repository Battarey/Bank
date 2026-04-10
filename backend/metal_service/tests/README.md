# Тестирование (tests)

Проверка точности получения и обработки котировок металлов.

## Структура тестов
- `/unit`: Мокирование HTTP-ответов внешнего API и проверка правильности математической конвертации унций в граммы.

## Запуск тестов
```powershell
docker compose run --rm -e APP_ENV=test metal_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest metal_service/tests/unit -v"
```
