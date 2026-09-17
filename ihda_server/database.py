"""Engine lifecycle and explicit schema initialization."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event, insert, select
from sqlalchemy.engine import make_url

from ihda_server import lifecycle_schema, tracking_schema  # noqa: F401
from ihda_server.database_policy import DatabaseTimeouts
from ihda_server.schema import metadata, versions

SCHEMA_VERSION = 3


def make_engine(url: str, *, timeouts: DatabaseTimeouts | None = None) -> Engine:
    policy = timeouts if timeouts is not None else DatabaseTimeouts()
    options = (
        {
            "connect_timeout": policy.connect_seconds,
            "options": policy.postgres_options,
        }
        if make_url(url).get_backend_name() == "postgresql"
        else {}
    )
    engine = create_engine(url, pool_pre_ping=True, connect_args=options)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def configure(connection: object, record: object) -> None:
            connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]
            connection.execute(f"PRAGMA busy_timeout={policy.lock_ms}")  # type: ignore[attr-defined]

    return engine


def initialize(engine: Engine) -> None:
    from sqlalchemy import inspect

    if inspect(engine).has_table(
        "team_schema",
        schema=engine.get_execution_options().get("schema_translate_map", {}).get(None),
    ):
        verify_schema(engine)
        return
    with engine.begin() as connection:
        metadata.create_all(connection)
        installed = connection.execute(select(versions.c.version)).scalar_one_or_none()
        if installed is None:
            from ihda_server.tracking import install

            install(connection)
            connection.execute(insert(versions).values(version=SCHEMA_VERSION))
        elif installed != SCHEMA_VERSION:
            raise RuntimeError(
                f"Unsupported schema {installed}; expected {SCHEMA_VERSION}"
            )


def verify_schema(engine: Engine) -> None:
    with engine.connect() as connection:
        if (
            connection.execute(select(versions.c.version)).scalar_one()
            != SCHEMA_VERSION
        ):
            raise RuntimeError("Database schema needs migration")
