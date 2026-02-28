"""Константы RabbitMQ: имена exchange, routing-key, очередей."""

# Exchange для всех уведомлений (topic)
NOTIFICATIONS_EXCHANGE = "notifications"

# Email
EMAIL_ROUTING_KEY = "email.send"
EMAIL_QUEUE = "email_queue"
