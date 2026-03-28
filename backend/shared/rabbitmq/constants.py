"""Константы RabbitMQ: имена exchange, routing-key, очередей."""

# Exchange для всех уведомлений (topic)
NOTIFICATIONS_EXCHANGE = "notifications"

# Email
EMAIL_ROUTING_KEY = "email.send"
EMAIL_QUEUE = "email_queue"

# Exchange для бизнес-логов (topic)
LOGS_EXCHANGE = "logs"

# Routing keys для различных типов событий
LOG_AUTH_KEY = "log.auth"
LOG_ACCOUNT_KEY = "log.account"
LOG_TRANSACTION_KEY = "log.transaction"

# Очередь для log_service
LOG_QUEUE = "log_queue"
