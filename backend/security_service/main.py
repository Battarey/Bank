"""Security Service — антифрод-мониторинг и AML-анализ банковских операций."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container

from .core.config import SecuritySettings

# Инициализация инфраструктуры (Settings, DB Engine, Session Factory)
bootstrap(SecuritySettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect
from shared.rabbitmq.client import disconnect as rmq_disconnect
from shared.utils.exceptions_handler import setup_exception_handlers

from .api.antifraud import router as check_router
from shared.mongodb_core import close_mongodb, init_mongodb, ping_mongodb

@asynccontextmanager
async def lifespan(_app: FastAPI):
	await rmq_connect()
	
	settings: SecuritySettings = container.settings
	mongo_indexes = [
		{
			"collection": settings.SECURITY_COLLECTION,
			"fields": [("created_at", 1)],
			"expireAfterSeconds": settings.SECURITY_TTL_DAYS * 86_400,
		}
	]
	await init_mongodb(settings.mongo.URL, indexes=mongo_indexes)
	
	yield
	await close_mongodb()
	await rmq_disconnect()
	await container.dispose()


app = FastAPI(
	title="Security Service",
	version="0.2.0",
	description=(
		"Внутренний сервис мониторинга безопасности: автоматическое выявление подозрительных операций и AML-проверка."
	),
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "security",
			"description": "Эндпоинты проверки транзакций и событий безопасности.",
		},
		{
			"name": "health",
			"description": "Проверка работоспособности сервиса.",
		},
	],
)

# Регистрация глобального обработчика ошибок BaseBusinessError
setup_exception_handlers(app)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
	"""Глубокая проверка работоспособности сервиса и его зависимостей."""
	from shared.rabbitmq.client import ping_rabbitmq

	mongo_ok = await ping_mongodb()
	rmq_ok = await ping_rabbitmq()

	overall_status = "ok" if mongo_ok and rmq_ok else "error"
	
	return {
		"status": overall_status,
		"dependencies": {
			"mongodb": "ok" if mongo_ok else "error",
			"rabbitmq": "ok" if rmq_ok else "error",
		},
	}


app.include_router(check_router)
