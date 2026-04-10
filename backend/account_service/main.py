"""Account Service — управление банковскими счетами: открытие, просмотр, блокировка и закрытие."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container
from shared.config import BaseAppSettings

# Инициализация инфраструктуры (Settings, DB Engine, Session Factory)
bootstrap(BaseAppSettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect
from shared.rabbitmq.client import disconnect as rmq_disconnect
from shared.utils.exceptions_handler import setup_exception_handlers

from .close_account.router import router as close_account_router
from .freeze_account.router import router as freeze_account_router
from .open_account.router import router as open_account_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
	await rmq_connect()
	yield
	await rmq_disconnect()
	await container.dispose()


app = FastAPI(
	title="Account Service",
	version="0.3.0",
	description="Сервис управления жизненным циклом банковских счетов: открытие, мониторинг, блокировка и закрытие.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "accounts",
			"description": "Операции со счетами: создание, получение списка, управление статусом (заморозка/закрытие).",
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


app.include_router(open_account_router)
app.include_router(close_account_router)
app.include_router(freeze_account_router)
