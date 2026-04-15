# Workers Layer (Message Consumers)

Фоновые обработчики очереди RabbitMQ.

## Состав
- `consumers.py` — Потребитель сообщений из очереди `log_queue`. Анализирует входящий поток и делегирует сохранение в `LogService`.

- **TTL Manager**: Внутри реализован механизм автоматической очистки старых записей в Postgres History.
