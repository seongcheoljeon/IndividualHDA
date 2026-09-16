"""Opaque, expiring bearer credentials. Only SHA-256 token digests are stored."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, delete, insert, select

from ihda_server.schema import tokens, users
from libs.team.contracts import Unauthorized


class TokenIdentity:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def authenticate(self, credential: str) -> str:
        digest = hashlib.sha256(credential.encode()).hexdigest()
        with self._engine.connect() as connection:
            row = (
                connection.execute(select(tokens).where(tokens.c.digest == digest))
                .mappings()
                .first()
            )
        if row is None or row["expires_at"] <= datetime.now(UTC).isoformat():
            raise Unauthorized("Invalid or expired credential")
        return str(row["user_id"])

    def create_user(self, name: str) -> str:
        if not name.strip() or len(name) > 120:
            raise ValueError("A user name of 1–120 characters is required")
        user_id = str(uuid4())
        with self._engine.begin() as connection:
            connection.execute(insert(users).values(id=user_id, name=name.strip()))
        return user_id

    def issue(self, user_id: str, days: int = 30) -> str:
        if not 1 <= days <= 365:
            raise ValueError("Token lifetime must be 1–365 days")
        credential = secrets.token_urlsafe(48)
        with self._engine.begin() as connection:
            connection.execute(
                insert(tokens).values(
                    digest=hashlib.sha256(credential.encode()).hexdigest(),
                    user_id=user_id,
                    expires_at=(datetime.now(UTC) + timedelta(days=days)).isoformat(),
                )
            )
        return credential

    def revoke_user(self, user_id: str) -> None:
        with self._engine.begin() as connection:
            connection.execute(delete(tokens).where(tokens.c.user_id == user_id))
