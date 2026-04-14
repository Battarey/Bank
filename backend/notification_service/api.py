from fastapi import FastAPI
from shared.rabbitmq.client import ping_rabbitmq
from .store.client import ping_mongo

app = FastAPI(title="Notification Service Health API")

@app.get("/health")
async def health_check():
	"""Глубокая проверка MongoDB (logs) и RabbitMQ."""
	mongo_ok = await ping_mongo()
	rmq_ok = await ping_rabbitmq()

	return {
		"status": "ok" if mongo_ok and rmq_ok else "error",
		"dependencies": {
			"mongodb_logs": "ok" if mongo_ok else "error",
			"rabbitmq": "ok" if rmq_ok else "error",
		}
	}
