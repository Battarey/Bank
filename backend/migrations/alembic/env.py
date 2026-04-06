import os
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv

# Interpret the config file for Python logging.
from shared.config import BaseAppSettings
from shared.bootstrap import bootstrap, get_container

# Инициализируем настройки для миграций
bootstrap(BaseAppSettings)
container = get_container()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, '..')))
from shared import models

# Метаданные моделей
target_metadata = models.base.Base.metadata


def _get_database_url() -> str:
    """Получает URL базы данных и конвертирует его в синхронный формат для Alembic."""
    url = container.db_settings.DATABASE_URL
    
    # Alembic работает в синхронном режиме, поэтому нам нужен драйвер psycopg (v3)
    from sqlalchemy.engine.url import make_url
    parsed = make_url(url)
    sync_url = parsed.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
    
    print(f"[alembic] Using sync URL for migrations: {sync_url}", flush=True)
    return sync_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_database_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()
    print(f"[alembic] run_migrations_online url: {configuration['sqlalchemy.url']}", flush=True)

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
