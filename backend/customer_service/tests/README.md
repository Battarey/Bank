# Тестирование (tests)

Гарантия корректности обработки персональных данных и процесса онбординга.

## Структура тестов
- `/unit`: Тестирование логики нормализации, валидации ИНН/СНИЛС и переходов состояний онбординга.

## Запуск тестов

### Локальный запуск
```powershell
pytest backend/customer_service/tests
```

### Запуск через Docker
```powershell
docker compose run --rm -e APP_ENV=test customer_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest customer_service/tests/unit -v"
```

### Тестирование онбординга
```powershell
pytest backend/customer_service/tests/integration/test_registration_flow.py
```

## Особенности
Тесты используют фикстуры для очистки Redis-черновиков между запусками, чтобы гарантировать изоляцию данных.
