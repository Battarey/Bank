# Тестирование (tests)

Валидация точности срабатывания антифрод-алгоритмов.

## Структура тестов
- `/unit`: Тестирование каждого отдельного правила из `rules.py` на граничных значениях сумм и частот.

## Запуск тестов
```powershell
docker compose run --rm -e APP_ENV=test security_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest security_service/tests/unit -v"
```
