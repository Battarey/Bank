# Gateway Service

![Go 1.23](https://img.shields.io/badge/go-1.23-00ADD8.svg)
![Echo](https://img.shields.io/badge/Echo-v4-blue.svg)
![Redis](https://img.shields.io/badge/Redis-7--alpine-D82C20.svg)
![Swagger](https://img.shields.io/badge/OpenAPI-3.0-green.svg)

Центральный API Gateway системы, обеспечивающий единую точку входа («Единое окно») для всех клиентских приложений. Реализует функции безопасности, маршрутизации и агрегированного мониторинга состояния (Deep Healthcheck).

## Архитектура

Написан на Go с использованием фреймворка Echo. Архитектура ориентирована на высокую пропускную способность и низкие задержки.

```text
gateway_service/
├── routes/          # Обработчики запросов и Deep Healthcheck
├── middleware/      # Auth, Rate Limiting, Request ID, UUID Validation
├── proxy/           # Централизованная логика проксирования и Ping-тесты
├── redis/           # Клиенты для сессий и онбординга
├── schemas/         # Общие DTO для ответов (Success, Error, Health)
├── config/          # Загрузка конфигурации (Config via Environment)
├── docs/            # Автогенерируемая документация Swagger/OpenAPI
├── tests/           # Интеграционные и unit-тесты на Go
├── main.go          # Инициализация и запуск сервера Echo
└── README.md
```

## Ключевые функции

1.  **Централизованная авторизация**: Middleware проверяет `X-Session-Token` в Redis для всех защищенных маршрутов (`/api/v1/...`).
2.  **Безопасность и Валидация**:
    -   **Rate Limiting**: Ограничение количества запросов для защиты от DoS-атак.
    -   **UUID Strict Validation**: Строгая проверка идентификаторов на уровне шлюза.
    -   **Internal Auth**: Автоматическая инъекция `X-Internal-Key` во все проксируемые запросы.
3.  **Обсервабельность (Observability)**:
    -   **X-Request-ID**: Сквозная трассировка запросов через всю микросервисную цепочку.
    -   **Deep Healthcheck**: Агрегированный мониторинг. Шлюз опрашивает все микросервисы, которые проверяют свои зависимости (БД, Брокеры).
4.  **Управление сессиями**: Поддержка "скользящих сессий" в Redis и механизмов мгновенного отзыва токенов.

## Технологии

-   **Go 1.23**: Язык разработки.
-   **Echo v4**: Высокопроизводительный веб-фреймворк.
-   **Go-Redis v9**: Асинхронный клиент Redis.
-   **Swag**: Инструмент генерации OpenAPI спецификаций.

## API Документация (Swagger)

Для обновления спецификации OpenAPI:
```bash
# Выполняется в корне gateway_service
docker run --rm -v ${PWD}:/code ghcr.io/swaggo/swag:v1.16.4 init
```

## Переменные окружения

| Ключ | Описание | Значение по умолчанию |
|------|----------|-----------------------|
| `PORT` | Порт входящих соединений | `8080` |
| `INTERNAL_API_KEY` | Секрет для аутентификации микросервисов | - |
| `REDIS_SESSIONS_URL` | Хранилище сессий | `redis://...` |
| `*_SERVICE_URL` | Адреса внутренних микросервисов | - |

## Запуск

Сборка и запуск через Docker Compose:
```bash
docker-compose up --build gateway_service
```
