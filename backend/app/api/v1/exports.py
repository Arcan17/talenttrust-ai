"""Dossier PDF export endpoint (US4, Phase 6).

Write role (org_admin/recruiter) may export. Requires an existing dossier (409 otherwise).
Returns an application/pdf attachment and emits the `pdf_exported` audit event.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.services import report_pdf

router = APIRouter(prefix="/candidates", tags=["exports"])

_writer = require_role(Role.org_admin, Role.recruiter)


@router.post("/{candidate_id}/dossier/export")
async def export_dossier(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(_writer),
) -> Response:
    try:
        pdf_bytes, filename = await report_pdf.export_dossier_pdf(
            db,
            organization_id=current.organization_id,
            actor_user_id=current.id,
            candidate_id=candidate_id,
        )
    except report_pdf.DossierRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except report_pdf.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
