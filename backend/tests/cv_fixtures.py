"""Helpers to build small, valid PDF/DOCX byte streams for offline tests."""
from __future__ import annotations

import io

ENGLISH_CV = (
    "John Smith\n"
    "Software Engineer\n"
    "Summary: Experienced backend developer with skills in Python and FastAPI.\n"
    "Experience: 5 years of work building APIs with Docker and PostgreSQL.\n"
    "Education: BSc Computer Science.\n"
    "Email: john.smith@example.org\n"
)

SPANISH_CV = (
    "Juan Pérez\n"
    "Desarrollador de Software\n"
    "Resumen: Desarrollador backend con experiencia en Python y FastAPI.\n"
    "Experiencia: 5 años de trabajo construyendo APIs con Docker y PostgreSQL.\n"
    "Educación: Ingeniería en Computación.\n"
    "Correo: juan.perez@ejemplo.cl\n"
)


def make_pdf(text: str) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    # Insert each line so PyMuPDF reliably extracts text.
    y = 72
    for line in text.splitlines():
        page.insert_text((72, y), line)
        y += 16
    data = doc.tobytes()
    doc.close()
    return data


def make_empty_pdf() -> bytes:
    """A PDF with a page but no text (stands in for an image-only/scanned CV)."""
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def make_docx(text: str) -> bytes:
    from docx import Document

    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
