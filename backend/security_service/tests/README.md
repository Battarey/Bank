# Тестирование (tests)

Валидация точности срабатывания антифрод-алгоритмов.

## Структура тестов
- `/unit`: Тестирование каждого отдельного правила из `rules.py` на граничных значениях сумм и частот.
- `/integration`: Полная проверка эндпоинта `/check` с имитацией записи в MongoDB.

## Запуск тестов

### Запуск всех тестов сервиса
```powershell
pytest backend/security_service/tests
```

### Тестирование логики AML-правил
```powershell
pytest backend/security_service/tests/unit/test_rules.py
```

## Требования
Для тестов требуется установленный `pytest-asyncio` и настройки в `conftest.py` для мокирования подключений к MongoDB.
