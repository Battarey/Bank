import os
import subprocess
from psycopg import connect
from sqlalchemy.engine.url import make_url


def _require_database_url() -> str:
    url = os.getenv("ALEMBIC_DATABASE_URL")
    if not url:
        raise RuntimeError("ALEMBIC_DATABASE_URL is not set; cannot reset database.")
    return url


def reset_schema(url: str) -> None:
    """Drop and recreate the public schema so every run starts fresh."""

    parsed = make_url(url)
    conninfo = parsed.set(drivername="postgresql").render_as_string(hide_password=False)

    print("[migrations] Resetting schema via", conninfo, flush=True)

    with connect(conninfo, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
            cur.execute("CREATE SCHEMA public;")
            cur.execute("GRANT ALL ON SCHEMA public TO CURRENT_USER;")
            cur.execute("GRANT ALL ON SCHEMA public TO public;")
            cur.execute("COMMENT ON SCHEMA public IS 'standard public schema';")


def run_migrations() -> None:
    """Invoke Alembic upgrade after resetting the schema."""

    print("[migrations] Running Alembic upgrade...", flush=True)
    subprocess.run(["alembic", "-c", "alembic.ini", "upgrade", "head"], check=True)


def main() -> None:
    url = _require_database_url()
    reset_schema(url)
    run_migrations()
    print("[migrations] Database reset complete.", flush=True)


if __name__ == "__main__":
    main()
