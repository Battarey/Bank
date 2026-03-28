import os
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv

# Interpret the config file for Python logging.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import sys
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, '..')))
from shared import models

# Placeholder metadata. Update when SQLAlchemy models appear.
target_metadata = models.base.Base.metadata


def _get_database_url() -> str:
    env_url = os.getenv("ALEMBIC_DATABASE_URL")
    if env_url:
        print(f"[alembic] Using ALEMBIC_DATABASE_URL: {env_url}", flush=True)
        return env_url
    raise RuntimeError("ALEMBIC_DATABASE_URL is not set; unable to run migrations.")


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
