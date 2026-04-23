# Этап 1
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /build

COPY currency_service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Этап 2
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONPATH=/app

WORKDIR /app

# Копируем установленные зависимости из builder-стейджа
COPY --from=builder /install /usr/local

# Копируем код сервиса и общую библиотеку
COPY currency_service /app/currency_service
COPY shared /app/shared

CMD ["uvicorn", "currency_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
