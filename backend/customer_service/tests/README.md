# Тестирование (tests)

Гарантия корректности обработки персональных данных и процесса онбординга.

## Структура тестов
- `/unit`: Тестирование логики нормализации, валидации ИНН/СНИЛС и переходов состояний онбординга.

## Запуск тестов
```powershell
docker compose run --rm -e APP_ENV=test customer_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest customer_service/tests/unit -v"
```
