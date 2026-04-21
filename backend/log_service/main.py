import asyncio
import logging

import uvicorn

from shared.bootstrap import bootstrap, get_container
from .core.config import LogSettings

# Инициализация инфраструктуры ДО импорта роутеров и воркеров
bootstrap(LogSettings)

from .api.router import app
from .workers.consumers import run_consumers

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("log_service")


async def run_services(settings: LogSettings):
	"""Запуск API и консьюмеров параллельно."""
	config = uvicorn.Config(app, host="0.0.0.0", port=settings.HEALTH_PORT, log_level="info")
	server = uvicorn.Server(config)
	
	# Запускаем и то, и другое
	await asyncio.gather(
		server.serve(),
		run_consumers()
	)


def main() -> None:
	"""Entry point."""
	# Настройки уже инициализированы при импорте модуля выше
	container = get_container()
	settings = container.settings

	try:
		asyncio.run(run_services(settings))
	except KeyboardInterrupt:
		logger.info("Прервано пользователем.")
	except Exception as exc:
		logger.exception("Критическая ошибка запуска: %s", exc)


if __name__ == "__main__":
	main()
