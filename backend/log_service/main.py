import asyncio
import logging

from shared.bootstrap import bootstrap

from .config import LogSettings
from .consumers import run_consumers

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("log_service")


def main() -> None:
	"""Entry point."""
	# Инициализация инфраструктуры на базе типизированных настроек
	bootstrap(LogSettings)
	
	try:
		asyncio.run(run_consumers())
	except KeyboardInterrupt:
		logger.info("Прервано пользователем.")
	except Exception as exc:
		logger.exception("Критическая ошибка запуска: %s", exc)


if __name__ == "__main__":
	main()
