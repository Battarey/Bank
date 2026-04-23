# Этап 1: Сборка зависимостей
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY log_service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Этап 2: Финальный образ
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Копируем установленные зависимости
COPY --from=builder /install /usr/local

# Копируем код сервиса и общую библиотеку
COPY shared /app/shared
COPY log_service /app/log_service

CMD ["python", "-m", "log_service.main"]
