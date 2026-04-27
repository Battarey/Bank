from fastapi import FastAPI
from shared.rabbitmq.client import ping_rabbitmq
from shared.mongodb_core import ping_mongodb
from shared.utils.monitoring import instrument_app

app = FastAPI(title="Notification Service Health API")

@app.get("/health")
async def health_check():
	"""Глубокая проверка MongoDB (logs) и RabbitMQ."""
	mongo_ok = await ping_mongodb()
	rmq_ok = await ping_rabbitmq()

	return {
		"status": "ok" if mongo_ok and rmq_ok else "error",
		"dependencies": {
			"mongodb_logs": "ok" if mongo_ok else "error",
			"rabbitmq": "ok" if rmq_ok else "error",
		}
	}

instrument_app(app)
