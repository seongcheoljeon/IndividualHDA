"""Explicit transactional upgrade; never run by request handling."""

from copy import deepcopy

from sqlalchemy import Engine, insert, select, update

from ihda_server import lifecycle_schema as lifecycle
from ihda_server import schema as tables
from libs.library_metadata import new_identity, version_details


def upgrade(engine: Engine) -> None:
    with engine.begin() as connection:
        installed = connection.execute(
            select(tables.versions.c.version).with_for_update()
        ).scalar_one()
        if installed == 2:
            return
        if installed != 1:
            raise RuntimeError(f"Unsupported schema {installed}")
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql(
                "LOCK TABLE team_schema IN ACCESS EXCLUSIVE MODE"
            )
        tables.metadata.create_all(connection)
        for row in connection.execute(select(tables.assets)).mappings().all():
            document = deepcopy(row["document"])
            asset_uuid = new_identity()
            current = None
            for history in (
                connection.execute(
                    select(tables.history)
                    .where(tables.history.c.asset_id == row["id"])
                    .order_by(tables.history.c.id)
                )
                .mappings()
                .all()
            ):
                version_uuid = new_identity()
                historical = deepcopy(history["document"])
                historical.update(asset_uuid=asset_uuid, version_uuid=version_uuid)
                details = version_details(historical)
                connection.execute(
                    insert(lifecycle.version_state).values(
                        history_id=history["id"], uuid=version_uuid, details=details
                    )
                )
                connection.execute(
                    update(tables.history)
                    .where(tables.history.c.id == history["id"])
                    .values(document=historical)
                )
                for kind, blob in historical.get("files", {}).items():
                    connection.execute(
                        insert(lifecycle.file_refs).values(
                            history_id=history["id"],
                            kind=kind,
                            **blob,
                            registered_at=historical.get("created_at"),
                            status="unverified",
                        )
                    )
                if history["version"] == row["document"]["version"]:
                    current = version_uuid
            connection.execute(
                insert(lifecycle.asset_state).values(
                    asset_id=row["id"],
                    uuid=asset_uuid,
                    current_version_uuid=current,
                    provenance={},
                )
            )
            if document.pop("favorite", False):
                for user in connection.execute(
                    select(tables.members.c.user_id).where(
                        tables.members.c.project_id == row["project_id"]
                    )
                ).scalars():
                    connection.execute(
                        insert(lifecycle.preferences).values(
                            asset_id=row["id"],
                            user_id=user,
                            favorite=1,
                            revision=1,
                            use_count=0,
                        )
                    )
            document.update(asset_uuid=asset_uuid, version_uuid=current)
            connection.execute(
                update(tables.assets)
                .where(tables.assets.c.id == row["id"])
                .values(document=document)
            )
        connection.execute(update(tables.versions).values(version=2))
