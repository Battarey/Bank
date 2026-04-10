# Тестирование (tests)

Набор тестов для проверки механизмов аутентификации и защиты данных.

## Структура тестов
- `/unit`: Тестирование логики хеширования bcrypt, генерации токенов сессий и обработки ошибок без внешних зависимостей.

## Ключевые сценарии
- **Brute-force protection**: Проверка того, что после 5 неудачных попыток активируется кулдаун.
- **Session validity**: Проверка TTL сессий и корректности Logout.
- **Recovery flow**: Тестирование полной цепочки разблокировки от запроса кода до смены статуса.

## Запуск тестов
```powershell
docker compose run --rm -e APP_ENV=test auth_service sh -c "pip install --no-cache-dir -r shared/requirements-test.txt && pytest auth_service/tests/unit -v"
```
