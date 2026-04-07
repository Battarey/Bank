# Тестирование (tests)

Валидация точности срабатывания антифрод-алгоритмов.

## Структура тестов
- `/unit`: Тестирование каждого отдельного правила из `rules.py` на граничных значениях сумм и частот.

## Запуск тестов

### Локальный запуск
```powershell
pytest backend/security_service/tests
```

### Запуск через Docker
```powershell
docker compose run --rm -e APP_ENV=test security_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest security_service/tests/unit -v"
```

### Тестирование логики AML-правил
```powershell
pytest backend/security_service/tests/unit/test_rules.py
```

## Требования
Для тестов требуется установленный `pytest-asyncio` и настройки в `conftest.py` для мокирования подключений к MongoDB.
