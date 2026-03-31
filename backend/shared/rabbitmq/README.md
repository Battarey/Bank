# RabbitMQ & Message Bus

Модуль для асинхронного межсервисного взаимодействия (**EDA**) через RabbitMQ. Обеспечивает публикацию доменных событий и доставку уведомлений.

---

## 🏗 Файловая архитектура
```
shared/rabbitmq/
├── bus.py         # Message Bus для трансляции событий из UoW
├── helpers.py     # Вспомогательные функции публикации (send_log, send_notification)
├── client.py      # Низкоуровневое подключение aio-pika
├── constants.py   # Имена обменников (Exchanges) и ключей маршрутизации
└── README.md
```

## Message Bus (bus.py)

Центральный компонент для обработки **Domain Events**.
-   **`MessageBus.handle(events)`**: Принимает список событий из `Unit of Work`.
-   **`MessageBus._publish(event)`**: Мапит событие на соответствующий RabbitMQ Exchange.
-   Автоматически обрабатывает `NotificationEvent` (отправка email) и `LogEvent` (аудит/аналитика).

## Полезные утилиты (helpers.py)

Функции для ручной регистрации событий (если не используется UoW):
-   **`send_notification(...)`**: Отправка Email-кода верификации, пароля и т.д.
-   **`send_log(...)`**: Запись бизнес-действия в глобальный аудит-лог.

## Константы и Роутинг (constants.py)

| Exchange         | Тип     | Routing Key       | Consumer                 |
|------------------|---------|-------------------|--------------------------|
| `notifications`  | `topic` | `email.send`      | `notification_service`   |
| `logs`           | `topic` | `log.auth`        | `log_service`            |
| `logs`           | `topic` | `log.account`     | `log_service`            |
| `logs`           | `topic` | `log.transaction` | `log_service`            |

## Пример использования

События автоматически отправляются в `RMQ` при вызове `uow.commit()`:
```python
uow.add_event(NotificationEvent(to="user@mail.ru", type="welcome"))
await uow.commit() # Событие попадет в MessageBus и улетит в RabbitMQ
```
