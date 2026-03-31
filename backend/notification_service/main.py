import asyncio
import logging
from .consumers import run_consumers

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("notification_service")


def main() -> None:
	"""Entry point."""
	try:
		asyncio.run(run_consumers())
	except KeyboardInterrupt:
		logger.info("Прервано пользователем.")
	except Exception as exc:
		logger.exception("Критическая ошибка запуска: %s", exc)


if __name__ == "__main__":
	main()
