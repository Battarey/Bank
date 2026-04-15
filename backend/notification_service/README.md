# Notification Service

Микросервис для отправки уведомлений пользователям (Email). Работает как фоновый воркер, асинхронно потребляющий задачи из RabbitMQ.

## Архитектура
Микросервис построен по принципам **Layered Architecture** и строго следует 4-х слойной структуре (api, services, repositories, core) с выделением слоев для воркеров и внешних интеграций.

### Файловая структура
```text
notification_service/
├── api/                # Слой API (Health Checks)
├── services/           # Слой Services: бизнес-логика и шаблоны
│   └── templates/      # HTML шаблоны писем
├── repositories/       # Слой Repositories: логирование в MongoDB
├── workers/            # Слой Workers: RabbitMQ консьюмеры (consumers.py)
├── clients/            # Слой Clients: SMTP клиент
├── core/               # Инфраструктурный слой: config.py
├── main.py             # Точка входа в приложение (API + Worker)
├── tests/              # Юнит-тесты
└── README.md
```

## Бизнес-логика
- **Источник событий**: RabbitMQ (`notifications` exchange).
- **Хранение**: История отправленных уведомлений и ошибок сохраняется в MongoDB (коллекция `email_log`).
- **TTL**: Записи в MongoDB автоматически удаляются через 90 дней (настраивается).
- **Шаблонизация**: Поддержка текстовых и HTML версий писем с динамической подстановкой переменных.

## 🛰 API Эндпоинты
| Метод | Путь                            | Описание                                  |
|-------|---------------------------------|-------------------------------------------|
| GET   | `/health`                       | Проверка состояния MongoDB и RabbitMQ     |

## Технологии
- **FastAPI**: Health Check API.
- **Aio-pika**: Асинхронная работа с RabbitMQ.
- **Motor**: Асинхронный драйвер MongoDB.
- **Aiosmtplib**: Асинхронная отправка Email.
