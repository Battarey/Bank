# Тестирование (tests)

Гарантия стабильности и безопасности API Gateway на языке Go.

## Типы тестов
- **Integration Tests**: Проверка полной цепочки запроса от входа в шлюз до взаимодействия с Redis Mock и получения ответа от прокси.
- **Middleware Tests**: Изолированная проверка логики AuthMiddleware, публичных путей и PIN-gate.

## Инструментарий
- **`testing`**: Стандартный пакет Go.
- **`net/http/httptest`**: Создание фиктивных HTTP-запросов и запись ответов.
- **`testify`**: (Опционально) для удобных утверждений (assertions).

## Запуск тестов

### Запуск всех тестов через Docker (Рекомендуется)
Если на вашей машине не установлена среда Go, используйте Docker:
```bash
docker run --rm -v "./gateway_service:/app" -v "./shared:/shared" -w /app golang:1.23-alpine go test ./tests -v
```

### Локальный запуск (требуется Go 1.23)
```bash
go test ./...
```

### Запуск с проверкой покрытия (Coverage)
```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

## Особенности
Поскольку шлюз сильно зависит от Redis, в тестах используется подмена реального клиента на Mock или локальный тестовый инстанс.
