"""Audit logging helper.

Writes append-only AuditLog rows for significant events (Constitution Principle VII).
The caller controls the transaction; `record` adds (and flushes) but does not commit
unless `commit=True`. Rows are never updated or deleted.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditEvent, AuditLog


async def record(
    db: AsyncSession,
    *,
    event: AuditEvent,
    organization_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    meta: dict | None = None,
    commit: bool = False,
) -> AuditLog:
    entry = AuditLog(
        event=event,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        meta=meta,
    )
    db.add(entry)
    await db.flush()
    if commit:
        await db.commit()
    return entry
