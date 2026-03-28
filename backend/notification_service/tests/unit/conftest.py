import os
import pytest

os.environ["RABBITMQ_URL"] = "amqp://guest:guest@localhost:5672/"
os.environ["MONGO_URL"] = "mongodb://localhost:27017/test_notifications_db"
os.environ["SMTP_HOST"] = "smtp.example.com"
os.environ["SMTP_PORT"] = "465"
os.environ["SMTP_USER"] = "test@example.com"
os.environ["SMTP_PASSWORD"] = "password"
os.environ["SMTP_FROM"] = "test@example.com"
os.environ["SMTP_USE_TLS"] = "true"
