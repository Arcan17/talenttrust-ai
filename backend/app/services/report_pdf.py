"""Dossier PDF export (ReportLab — chosen for the MVP per research.md R7).

Renders the candidate dossier (summary, score + breakdown, evidence-based skills, gaps, neutral
inconsistencies, interview questions) plus the recorded human decision (if any) and a short legal
note that the non-binding AI recommendation is not an automated hiring decision (Principle IX).
Pure, offline rendering — no network. Orchestration loads org-scoped data, emits `pdf_exported`,
and requires an existing dossier (409 otherwise).
"""
from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditEvent
from app.models.candidate import Candidate
from app.models.decision import Decision
from app.models.dossier import Dossier
from app.models.score import Score
from app.models.vacancy import Vacancy
from app.services import audit_service

LEGAL_NOTE = (
    "Nota legal: la recomendación generada por IA es de carácter orientativo y NO constituye una "
    "decisión automática de contratación. La decisión final corresponde siempre a una persona."
)


class NotFoundError(Exception):
    """Candidate/vacancy not found within the caller's organization."""


class DossierRequiredError(Exception):
    """A dossier must exist before it can be exported."""


def _p(text: str, style) -> Paragraph:
    return Paragraph(escape(str(text)), style)


def render_dossier_pdf(
    *,
    candidate: Candidate,
    vacancy: Vacancy,
    dossier: Dossier,
    score: Score,
    decision: Decision | None,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm, title="TalentTrust AI — Dossier",
    )
    styles = getSampleStyleSheet()
    h1, h2, body, small = (
        styles["Title"], styles["Heading2"], styles["BodyText"], styles["Italic"]
    )
    story: list = []

    # Header
    story.append(_p("TalentTrust AI — Candidate Dossier", h1))
    story.append(_p(f"Candidato: {candidate.display_name or candidate.id}", body))
    story.append(_p(f"Vacante: {vacancy.title}", body))
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    story.append(_p(f"Fecha de generación: {generated_at}", body))
    story.append(Spacer(1, 6 * mm))

    # Summary + score + recommendation
    story.append(_p("Resumen", h2))
    story.append(_p(dossier.summary_text or "Sin resumen disponible.", body))
    story.append(_p(f"Score total: {score.value} / 100", body))
    story.append(_p(f"Recomendación IA (no vinculante): {score.recommendation.value}", body))
    story.append(Spacer(1, 4 * mm))

    # Score breakdown table
    story.append(_p("Score — desglose", h2))
    rows = [["Factor", "Peso", "Sub-score", "Ponderado"]]
    for item in score.breakdown:
        rows.append([
            str(item.get("factor", "")),
            str(item.get("weight", "")),
            str(item.get("sub_score", "")),
            str(item.get("weighted", "")),
        ])
    table = Table(rows, hAlign="LEFT")
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ])
    )
    story.append(table)
    story.append(Spacer(1, 4 * mm))

    # Skills with evidence
    story.append(_p("Skills detectadas (con evidencia)", h2))
    if dossier.skills:
        items = []
        for s in dossier.skills:
            ev = "; ".join(f"{e.get('source')}: {e.get('detail')}" for e in s.get("evidence", []))
            req = " [obligatoria]" if s.get("required") else ""
            items.append(ListItem(_p(f"{s.get('name')}{req} — {ev}", body)))
        story.append(ListFlowable(items, bulletType="bullet"))
    else:
        story.append(_p("No se detectaron skills.", body))
    story.append(Spacer(1, 4 * mm))

    # Gaps
    story.append(_p("Brechas", h2))
    if dossier.gaps:
        items = [
            ListItem(_p(f"{g.get('requirement')}: {g.get('note')}", body))
            for g in dossier.gaps
        ]
        story.append(ListFlowable(items, bulletType="bullet"))
    else:
        story.append(_p("No se identificaron brechas.", body))
    story.append(Spacer(1, 4 * mm))

    # Inconsistencies (neutral)
    story.append(_p("Inconsistencias (requieren revisión)", h2))
    if dossier.inconsistencies:
        items = [
            ListItem(_p(f"[{i.get('severity')}] {i.get('message')}", body))
            for i in dossier.inconsistencies
        ]
        story.append(ListFlowable(items, bulletType="bullet"))
    else:
        story.append(_p("No se registraron inconsistencias.", body))
    story.append(Spacer(1, 4 * mm))

    # Interview questions
    story.append(_p("Preguntas de entrevista sugeridas", h2))
    if dossier.interview_questions:
        items = [ListItem(_p(q.get("question", ""), body)) for q in dossier.interview_questions]
        story.append(ListFlowable(items, bulletType="1"))
    else:
        story.append(_p("Sin preguntas sugeridas.", body))
    story.append(Spacer(1, 4 * mm))

    # Human decision (if any)
    story.append(_p("Decisión humana registrada", h2))
    if decision is not None:
        story.append(_p(f"Resultado: {decision.human_outcome.value}", body))
        story.append(_p(f"Recomendación IA al decidir: {decision.ai_recommendation.value}", body))
        if decision.note:
            story.append(_p(f"Nota: {decision.note}", body))
        story.append(_p(f"Fecha: {decision.decided_at.strftime('%Y-%m-%d %H:%M UTC')}", body))
    else:
        story.append(_p("Aún no se ha registrado una decisión humana.", body))
    story.append(Spacer(1, 8 * mm))

    # Legal note
    story.append(_p(LEGAL_NOTE, small))

    doc.build(story)
    return buf.getvalue()


async def export_dossier_pdf(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> tuple[bytes, str]:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")

    dossier = await db.scalar(select(Dossier).where(Dossier.candidate_id == candidate_id))
    if dossier is None:
        raise DossierRequiredError("A dossier is required before exporting")

    vacancy = await db.get(Vacancy, candidate.vacancy_id)
    if vacancy is None or vacancy.organization_id != organization_id:
        raise NotFoundError("Vacancy not found")

    score = await db.scalar(select(Score).where(Score.candidate_id == candidate_id))
    decision = await db.scalar(
        select(Decision)
        .where(Decision.candidate_id == candidate_id)
        .order_by(Decision.decided_at.desc(), Decision.created_at.desc())
    )
    if score is None:
        # A dossier always has a score; guard defensively.
        raise DossierRequiredError("Score not found for this dossier")

    pdf_bytes = render_dossier_pdf(
        candidate=candidate, vacancy=vacancy, dossier=dossier, score=score, decision=decision
    )

    await audit_service.record(
        db,
        event=AuditEvent.pdf_exported,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_type="candidate",
        target_id=candidate_id,
        meta={"bytes": len(pdf_bytes), "has_decision": decision is not None},
    )
    await db.commit()

    filename = f"talenttrust-dossier-{candidate_id}.pdf"
    return pdf_bytes, filename
