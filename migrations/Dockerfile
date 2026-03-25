FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps (psycopg, etc.)
RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential libpq-dev \
	&& rm -rf /var/lib/apt/lists/*

COPY migrations/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем shared для доступа к моделям в alembic
COPY shared ./shared
COPY migrations .

CMD ["python", "reset_and_upgrade.py"]
