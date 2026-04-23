# Этап 1: Сборка зависимостей
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Устанавливаем системные зависимости, необходимые для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY migrations/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Этап 2: Финальный образ
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Копируем установленные зависимости
COPY --from=builder /install /usr/local

# Копируем shared для доступа к моделям в alembic
COPY shared ./shared
COPY migrations .

CMD ["python", "reset_and_upgrade.py"]
