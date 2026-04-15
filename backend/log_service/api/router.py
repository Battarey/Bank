from fastapi import FastAPI
from shared.rabbitmq.client import ping_rabbitmq
from shared.clickhouse_core.client import ping_clickhouse
from shared.history_core.db import ping_db as ping_history_db

app = FastAPI(title="Log Service Health API")

@app.get("/health")
async def health_check():
	"""Глубокая проверка ClickHouse и Postgres History."""
	ch_ok = await ping_clickhouse()
	db_ok = await ping_history_db()
	rmq_ok = await ping_rabbitmq()

	return {
		"status": "ok" if ch_ok and db_ok and rmq_ok else "error",
		"dependencies": {
			"clickhouse": "ok" if ch_ok else "error",
			"postgres_history": "ok" if db_ok else "error",
			"rabbitmq": "ok" if rmq_ok else "error",
		}
	}
