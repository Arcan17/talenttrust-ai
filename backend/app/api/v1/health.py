"""Health/readiness endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - exercised only when DB is down
        db_status = "error"
    return {"status": "ok", "database": db_status}
