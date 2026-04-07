# Тестирование (tests)

Проверка точности получения и обработки котировок металлов.

## Структура тестов
- `/unit`: Мокирование HTTP-ответов внешнего API и проверка правильности математической конвертации унций в граммы.
- `/integration`: Проверка работы кеширования в Redis и корректности формирования ответов FastAPI.

## Запуск тестов

### Локальный запуск
```powershell
pytest backend/metal_service/tests
```

### Запуск через Docker
```powershell
docker compose run --rm -e APP_ENV=test metal_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest metal_service/tests/unit -v"
```

### Проверка логики конвертации
```powershell
pytest backend/metal_service/tests/unit/test_conversion.py
```

## Требования
Для корректной работы тестов требуются установленные зависимости и доступ к тестовому инстансу Redis.
