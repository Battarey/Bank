# rabbitmq

Общий модуль для работы с RabbitMQ (aio-pika). Предоставляет подключение и публикацию сообщений.

## Файловая архитектура

```
shared/rabbitmq/
├── __init__.py       # Публичный API модуля
├── client.py         # Подключение, отключение, publish()
├── constants.py      # Имена exchange, routing key, очередей
└── README.md
```

## Использование

### Подключение (в lifespan сервиса)

```python
from shared.rabbitmq import connect, disconnect

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    yield
    await disconnect()
```

## Константы (`constants.py`)

| Константа                | Значение          | Описание                        |
|--------------------------|-------------------|---------------------------------|
| `NOTIFICATIONS_EXCHANGE` | `notifications`   | Topic exchange для уведомлений  |
| `EMAIL_ROUTING_KEY`      | `email.send`      | Routing key для email-сообщений |
| `EMAIL_QUEUE`            | `email_queue`     | Очередь email (используется consumer) |
