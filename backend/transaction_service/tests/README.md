# Тестирование (tests)

Проверка надежности и корректности финансовых потоков.

## Структура тестов
- `/unit`: Изолированная проверка логики списаний, пополнений и конвертации валют с моками внешних сервисов.

## Ключевые проверки
- **Balance Invariant**: Проверка того, что сумма балансов после перевода (с учетом курса) изменилась корректно.
- **Idempotency Check**: Попытка повторной отправки одной и той же транзакции с тем же ключом.
- **Security Rejection**: Имитация блокировки от антифрода и проверка заморозки счёта.

## Запуск тестов
```powershell
docker compose run --rm -e APP_ENV=test transaction_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest transaction_service/tests/unit -v"  
```
