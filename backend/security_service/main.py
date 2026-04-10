"""Security Service — антифрод-мониторинг и AML-анализ банковских операций."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container

from .config import SecuritySettings

# Инициализация инфраструктуры (Settings, DB Engine, Session Factory)
bootstrap(SecuritySettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect
from shared.rabbitmq.client import disconnect as rmq_disconnect
from shared.utils.exceptions_handler import setup_exception_handlers

from .check.router import router as check_router
from .store import close_mongo, init_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
	await rmq_connect()
	await init_mongo()
	yield
	await close_mongo()
	await rmq_disconnect()
	await container.dispose()


app = FastAPI(
	title="Security Service",
	version="0.2.0",
	description="Внутренний сервис мониторинга безопасности: автоматическое выявление подозрительных операций и AML-проверка.",
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
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(check_router)
