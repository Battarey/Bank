# API Layer (Health Check)

Слой API для мониторинга состояния сервиса.

## Состав
- `router.py` — Эндпоинт `/health` для глубокой проверки зависимостей (MongoDB, RabbitMQ).

## Особенности
- В `notification_service` API используется преимущественно для инфраструктурных проверок (Health Checks), так как основная работа выполняется в фоне через RabbitMQ.
