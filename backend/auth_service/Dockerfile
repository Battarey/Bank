FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONPATH=/app

WORKDIR /app

COPY auth_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY auth_service /app/auth_service
COPY shared /app/shared

CMD ["uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
