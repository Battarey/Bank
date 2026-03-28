FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONPATH=/app

WORKDIR /app

COPY transaction_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY transaction_service /app/transaction_service
COPY shared /app/shared

CMD ["uvicorn", "transaction_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
