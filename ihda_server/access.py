"""Project-scoped database access: connection, lock and authorization as one step.

Every read or write against a project goes through ``reading()`` or
``writing()``, so a new catalog method cannot forget the permission check.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, select, update

from ihda_server import schema as tables
from ihda_server.lifecycle import LifecycleStore
from libs.team.contracts import Forbidden


class ProjectAccess:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self.lifecycle = LifecycleStore()

    @staticmethod
    def authorize(
        connection: Connection,
        project_id: str,
        user_id: str,
        write: bool = False,
        owner: bool = False,
    ) -> str:
        role = connection.execute(
            select(tables.members.c.role).where(
                tables.members.c.project_id == project_id,
                tables.members.c.user_id == user_id,
            )
        ).scalar_one_or_none()
        if role is None or (write and role == "viewer") or (owner and role != "owner"):
            raise Forbidden("Project permission denied")
        return str(role)

    @staticmethod
    def lock(connection: Connection, project_id: str) -> None:
        result = connection.execute(
            update(tables.projects)
            .where(tables.projects.c.id == project_id)
            .values(revision=tables.projects.c.revision)
        )
        if result.rowcount != 1:
            raise Forbidden("Project permission denied")

    @contextmanager
    def browsing(self) -> Iterator[Connection]:
        """A read connection outside any project (the caller's own project list)."""
        with self._engine.connect() as connection:
            yield connection

    @contextmanager
    def reading(
        self,
        project_id: str,
        user_id: str,
        *,
        write: bool = False,
        owner: bool = False,
        snapshot: bool = False,
    ) -> Iterator[Connection]:
        """An authorized read connection; ``snapshot`` pins one snapshot on Postgres."""
        with self._engine.connect() as connection:
            if snapshot and connection.dialect.name == "postgresql":
                connection = connection.execution_options(
                    isolation_level="REPEATABLE READ"
                )
            self.authorize(connection, project_id, user_id, write=write, owner=owner)
            yield connection

    @contextmanager
    def writing(
        self, project_id: str, user_id: str, *, write: bool = True, owner: bool = False
    ) -> Iterator[Connection]:
        """A transaction holding the project lock, with the caller authorized."""
        with self._engine.begin() as connection:
            self.lock(connection, project_id)
            self.authorize(connection, project_id, user_id, write=write, owner=owner)
            yield connection

    @contextmanager
    def creating(self) -> Iterator[Connection]:
        """A transaction without a project: any signed-in user may create one."""
        with self._engine.begin() as connection:
            yield connection
