"""Read-only catalog queries; SqlCatalog adds the writes."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    and_,
    func,
    or_,
    select,
)

from ihda_server import lifecycle_schema as state
from ihda_server import schema as tables
from ihda_server.access import ProjectAccess
from ihda_server.tracking import team_tracking
from libs.search_limits import QUERY_TEXT_MAX, TEAM_PAGE_DEFAULT, TEAM_PAGE_MAX
from libs.team.contracts import (
    DEFAULT_AUDIT_EVENT_LIMIT,
    NotFound,
    Page,
    TeamError,
)


class CatalogQueries(ProjectAccess):
    def projects(self, user_id: str) -> list[dict[str, Any]]:
        with self.browsing() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(tables.projects, tables.members.c.role)
                    .join(tables.members)
                    .where(tables.members.c.user_id == user_id)
                    .order_by(tables.projects.c.name)
                ).mappings()
            ]

    def members(self, project_id: str, user_id: str) -> list[dict[str, Any]]:
        with self.reading(project_id, user_id, owner=True) as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(
                        tables.members.c.user_id,
                        tables.members.c.role,
                        tables.users.c.name,
                    )
                    .join(tables.users)
                    .where(tables.members.c.project_id == project_id)
                ).mappings()
            ]

    def blob_size(self, project_id: str, user_id: str, digest: str) -> int:
        with self.reading(project_id, user_id) as connection:
            size = connection.execute(
                select(tables.blobs.c.size).where(
                    tables.blobs.c.project_id == project_id,
                    tables.blobs.c.digest == digest,
                )
            ).scalar_one_or_none()
            if size is None:
                raise NotFound("File does not belong to this project")
            return int(size)

    def list_assets(
        self,
        project_id: str,
        user_id: str,
        query: str = "",
        offset: int = 0,
        limit: int = TEAM_PAGE_DEFAULT,
    ) -> Page:
        if offset < 0 or not 1 <= limit <= TEAM_PAGE_MAX or len(query) > QUERY_TEXT_MAX:
            raise TeamError("Invalid pagination or query")
        # One snapshot for count, rows and revision: clients use the revision
        # for optimistic locking, so it must belong to the rows it accompanies.
        with self.reading(project_id, user_id, snapshot=True) as connection:
            criteria = [
                tables.assets.c.project_id == project_id,
                tables.assets.c.id.in_(
                    select(state.asset_state.c.asset_id).where(
                        state.asset_state.c.deleted_at.is_(None)
                    )
                ),
            ]
            if query.strip():
                pattern = (
                    "%"
                    + query.strip()
                    .replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                    + "%"
                )
                criteria.append(
                    or_(
                        tables.assets.c.name.ilike(pattern, escape="\\"),
                        tables.assets.c.category.ilike(pattern, escape="\\"),
                    )
                )
            total = connection.execute(
                select(func.count()).select_from(tables.assets).where(*criteria)
            ).scalar_one()
            # One LEFT JOIN instead of a preference SELECT per listed asset.
            mine = state.preferences
            rows = (
                connection.execute(
                    select(
                        tables.assets.c.document,
                        mine.c.favorite,
                        mine.c.revision,
                        mine.c.use_count,
                        mine.c.last_used_at,
                    )
                    .select_from(
                        tables.assets.outerjoin(
                            mine,
                            and_(
                                mine.c.asset_id == tables.assets.c.id,
                                mine.c.user_id == user_id,
                            ),
                        )
                    )
                    .where(*criteria)
                    .order_by(tables.assets.c.name_key, tables.assets.c.id)
                    .offset(offset)
                    .limit(limit)
                )
                .mappings()
                .all()
            )
            revision = connection.execute(
                select(tables.projects.c.revision).where(
                    tables.projects.c.id == project_id
                )
            ).scalar_one()
            return Page(
                [
                    self.lifecycle.apply_preference(
                        row["document"], self.lifecycle.preference_row(row, user_id)
                    )
                    for row in rows
                ],
                total,
                offset,
                limit,
                revision,
            )

    def get_asset(self, project_id: str, user_id: str, asset_id: int) -> dict[str, Any]:
        with self.reading(project_id, user_id) as connection:
            document = connection.execute(
                select(tables.assets.c.document).where(
                    tables.assets.c.project_id == project_id,
                    tables.assets.c.id == asset_id,
                )
            ).scalar_one_or_none()
            if document is None:
                raise NotFound("Asset does not exist")
            info = self.lifecycle.asset_state(connection, asset_id)
            if info["deleted_at"]:
                raise NotFound("Asset is in the trash")
            document = {
                **document,
                "dependencies": team_tracking(connection, project_id).dependencies(
                    document["version_uuid"]
                ),
            }
            return self.lifecycle.decorate(connection, document, user_id)

    def histories(
        self, project_id: str, user_id: str, asset_id: int
    ) -> list[dict[str, Any]]:
        with self.reading(project_id, user_id) as connection:
            rows = [
                dict(row)
                for row in connection.execute(
                    select(
                        tables.history.c.id,
                        tables.history.c.version,
                        tables.history.c.document,
                    )
                    .where(
                        tables.history.c.project_id == project_id,
                        tables.history.c.asset_id == asset_id,
                        tables.history.c.id.in_(
                            select(state.version_state.c.history_id).where(
                                state.version_state.c.deleted_at.is_(None)
                            )
                        ),
                        tables.history.c.asset_id.in_(
                            select(state.asset_state.c.asset_id).where(
                                state.asset_state.c.deleted_at.is_(None)
                            )
                        ),
                    )
                    .order_by(tables.history.c.id.desc())
                ).mappings()
            ]

            tracking = team_tracking(connection, project_id)
            dependencies = tracking.dependencies_many(
                [row["document"]["version_uuid"] for row in rows]
            )
            for row in rows:
                row["document"] = {
                    **row["document"],
                    "dependencies": dependencies.get(
                        row["document"]["version_uuid"], []
                    ),
                }
            return rows

    def trash(self, project_id: str, user_id: str) -> list[dict[str, Any]]:
        with self.reading(project_id, user_id) as connection:
            rows = [
                dict(row)
                for row in connection.execute(
                    select(
                        tables.assets.c.id,
                        tables.assets.c.name,
                        tables.assets.c.revision,
                        state.asset_state.c.deleted_at,
                        state.asset_state.c.uuid.label("asset_uuid"),
                    )
                    .join(state.asset_state)
                    .where(
                        tables.assets.c.project_id == project_id,
                        state.asset_state.c.deleted_at.is_not(None),
                    )
                ).mappings()
            ]
            for item in rows:
                item["asset_id"] = item.pop("id")
                item["history_id"] = None
            for row in connection.execute(
                select(
                    tables.assets.c.id,
                    tables.assets.c.name,
                    tables.assets.c.revision,
                    tables.history.c.id.label("history_id"),
                    tables.history.c.version,
                    state.version_state.c.deleted_at,
                    state.asset_state.c.uuid.label("asset_uuid"),
                    state.version_state.c.uuid.label("version_uuid"),
                )
                .select_from(tables.assets)
                .join(tables.history)
                .join(state.version_state)
                .join(
                    state.asset_state,
                    state.asset_state.c.asset_id == tables.assets.c.id,
                )
                .where(
                    tables.assets.c.project_id == project_id,
                    state.asset_state.c.deleted_at.is_(None),
                    state.version_state.c.deleted_at.is_not(None),
                )
            ).mappings():
                item = dict(row)
                item["asset_id"] = item.pop("id")
                rows.append(item)
            return rows

    def events(
        self,
        project_id: str,
        user_id: str,
        asset_uuid: str,
        offset: int = 0,
        limit: int = DEFAULT_AUDIT_EVENT_LIMIT,
    ) -> list[dict[str, Any]]:
        if offset < 0 or not 1 <= limit <= DEFAULT_AUDIT_EVENT_LIMIT:
            raise TeamError("Invalid pagination")
        with self.reading(project_id, user_id) as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(state.audit, tables.users.c.name.label("actor_name"))
                    .outerjoin(tables.users, tables.users.c.id == state.audit.c.actor)
                    .where(
                        state.audit.c.project_id == project_id,
                        state.audit.c.asset_uuid == asset_uuid,
                    )
                    .order_by(state.audit.c.occurred_at.desc())
                    .offset(offset)
                    .limit(limit)
                ).mappings()
            ]

    def file_status(
        self, project_id: str, user_id: str, asset_id: int
    ) -> list[dict[str, Any]]:
        with self.reading(project_id, user_id) as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(
                        tables.history.c.version,
                        state.file_refs.c.kind,
                        state.file_refs.c.filename,
                        state.file_refs.c.status,
                    )
                    .join(tables.history)
                    .where(
                        tables.history.c.asset_id == asset_id,
                        tables.history.c.project_id == project_id,
                    )
                ).mappings()
            ]

    def copy_check(
        self,
        project_id: str,
        user_id: str,
        name: str,
        category: str,
        library_uuid: str,
        asset_uuid: str,
    ) -> dict[str, Any]:
        from ihda_server.copy_import import copy_matches

        with self.reading(project_id, user_id) as connection:
            return copy_matches(
                connection,
                project_id,
                name,
                category,
                {"library_uuid": library_uuid, "asset_uuid": asset_uuid},
            )

    def tracking_read(
        self,
        project_id: str,
        user_id: str,
        kind: str,
        asset_uuid: str,
        version_uuid: str | None = None,
        offset: int = 0,
        limit: int = TEAM_PAGE_DEFAULT,
    ) -> list[dict[str, Any]]:
        try:
            with self.reading(project_id, user_id) as connection:
                return team_tracking(connection, project_id).read(
                    kind, asset_uuid, version_uuid, offset, limit
                )
        except ValueError as error:
            raise TeamError(str(error)) from error
