"""Durable, account-namespaced scene delivery. An import never waits for HTTP."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

from libs.database.rows import named_query
from libs.library_metadata import new_identity


class SceneOutbox:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS identity (singleton INTEGER PRIMARY KEY, uuid TEXT NOT NULL)"
            )
            db.execute(
                "INSERT OR IGNORE INTO identity (singleton,uuid) VALUES(1,:new_identity)",
                {"new_identity": new_identity()},
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS pending (id TEXT PRIMARY KEY,namespace TEXT NOT NULL,body TEXT NOT NULL,error TEXT)"
            )
            self.client_id = db.execute("SELECT uuid FROM identity").fetchone()[0]

    def enqueue(self, namespace: str, values: dict[str, Any]) -> str:
        identity = new_identity()
        body = {
            "request_id": identity,
            "operation": "scene",
            "values": {**values, "client_id": self.client_id},
        }
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT INTO pending (id,namespace,body,error) VALUES(:identity,:namespace,:body,NULL)",
                {
                    "identity": identity,
                    "namespace": namespace,
                    "body": json.dumps(body),
                },
            )
        return identity

    def flush(self, namespace: str, send: Callable[[dict[str, Any]], Any]) -> int:
        with closing(sqlite3.connect(self.path)) as db:
            rows = named_query(
                db,
                "SELECT id,body FROM pending WHERE namespace=:namespace ORDER BY (error IS NOT NULL),rowid LIMIT 100",
                {"namespace": namespace},
            ).fetchall()
            for row in rows:
                identity, body = row["id"], row["body"]
                try:
                    send(json.loads(body))
                except Exception as error:
                    with db:
                        db.execute(
                            "UPDATE pending SET error=:error WHERE id=:identity",
                            {"error": str(error), "identity": identity},
                        )
                    # A removed version must not stop newer observations. Network/
                    # authorization failures stop this pass to avoid request storms.
                    if isinstance(error, ValueError) or getattr(
                        error, "status", None
                    ) in {400, 404, 409, 422}:
                        continue
                    break
                with db:
                    db.execute(
                        "DELETE FROM pending WHERE id=:identity AND namespace=:namespace",
                        {"identity": identity, "namespace": namespace},
                    )
            return db.execute(
                "SELECT COUNT(*) FROM pending WHERE namespace=:namespace",
                {"namespace": namespace},
            ).fetchone()[0]
