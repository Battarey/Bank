import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from psycopg import connect
from sqlalchemy.engine.url import make_url

# Добавляем путь к корню backend, чтобы импортировать shared
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, "..")))

from shared.bootstrap import bootstrap, get_container
from shared.config import BaseAppSettings


def wait_for_host(host: str, port: int, timeout: int = 30) -> None:
	"""Ожидает доступности хоста по TCP."""
	start_time = time.time()
	while True:
		try:
			with socket.create_connection((host, port), timeout=1):
				return
		except (TimeoutError, ConnectionRefusedError, socket.gaierror):
			if time.time() - start_time > timeout:
				raise TimeoutError(f"Could not connect to {host}:{port}") from None
			time.sleep(1)


def _require_database_url() -> str:
	"""Инициализирует настройки и возвращает URL базы данных."""
	bootstrap(BaseAppSettings)
	url = get_container().db_settings.DATABASE_URL
	return url


def reset_schema(url: str) -> None:
	"""Drop and recreate the public schema so every run starts fresh."""

	parsed = make_url(url)
	conninfo = parsed.set(drivername="postgresql").render_as_string(hide_password=False)

	with connect(conninfo, autocommit=True) as conn:
		with conn.cursor() as cur:
			cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
			cur.execute("CREATE SCHEMA public;")
			cur.execute("GRANT ALL ON SCHEMA public TO CURRENT_USER;")
			cur.execute("GRANT ALL ON SCHEMA public TO public;")
			cur.execute("COMMENT ON SCHEMA public IS 'standard public schema';")


def run_migrations() -> None:
	"""Invoke Alembic upgrade after resetting the schema."""

	subprocess.run(["alembic", "-c", "alembic.ini", "upgrade", "head"], check=True)


def main() -> None:
	url = _require_database_url()
	parsed = make_url(url)

	# Ждем доступности хоста перед началом работы
	if parsed.host:
		wait_for_host(parsed.host, parsed.port or 5432)

	reset_schema(url)
	run_migrations()


if __name__ == "__main__":
	main()
