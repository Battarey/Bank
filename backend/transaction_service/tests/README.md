# Тестирование (tests)

Проверка надежности и корректности финансовых потоков.

## Структура тестов
- `/unit`: Изолированная проверка логики списаний, пополнений и конвертации валют с моками внешних сервисов.

## Ключевые проверки
- **Balance Invariant**: Проверка того, что сумма балансов после перевода (с учетом курса) изменилась корректно.
- **Idempotency Check**: Попытка повторной отправки одной и той же транзакции с тем же ключом.
- **Security Rejection**: Имитация блокировки от антифрода и проверка заморозки счёта.

### Запуск всех unit-тестов через Docker (Рекомендуемо)
```powershell
docker compose -f backend/docker-compose.yaml run --rm -e APP_ENV=test transaction_service sh -c "pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r shared/requirements-test.txt && pytest transaction_service/tests/unit -v"
```

### Запуск локально
```powershell
pytest transaction_service/tests/unit
```

## Запуск тестов

### Запуск всех тестов сервиса
```powershell
pytest backend/transaction_service/tests
```

### Тестирование переводов
```powershell
pytest backend/transaction_service/tests/unit/test_transfer_service.py
```