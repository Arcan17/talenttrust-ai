"""T034 (Phase 4a subset) — cv_parser: extraction, validation, ES+EN support.

Deterministic and offline (no LLM/network). Scoring/dossier are out of scope here.
"""
from __future__ import annotations

import pytest

from app.services import cv_parser
from tests.cv_fixtures import (
    ENGLISH_CV,
    SPANISH_CV,
    make_docx,
    make_empty_pdf,
    make_pdf,
)


def _parse(filename, ctype, data, max_size=None):
    return cv_parser.parse_cv(
        filename=filename, declared_content_type=ctype, data=data, max_size=max_size
    )


def test_parse_english_pdf():
    content_type, parsed, raw = _parse("cv.pdf", "application/pdf", make_pdf(ENGLISH_CV))
    assert content_type == "pdf"
    assert parsed.language == "en"
    assert "john.smith@example.org" in parsed.emails
    assert "python" in parsed.skills and "fastapi" in parsed.skills
    assert "FastAPI" in raw


def test_parse_spanish_docx():
    content_type, parsed, raw = _parse(
        "cv.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        make_docx(SPANISH_CV),
    )
    assert content_type == "docx"
    assert parsed.language == "es"
    assert "juan.perez@ejemplo.cl" in parsed.emails
    assert "docker" in parsed.skills


def test_reject_unsupported_format():
    with pytest.raises(cv_parser.UnsupportedFormatError):
        _parse("cv.txt", "text/plain", b"just some text")


def test_reject_oversize_file():
    big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 10)
    with pytest.raises(cv_parser.FileTooLargeError):
        _parse("big.pdf", "application/pdf", big)


def test_reject_pdf_without_text():
    with pytest.raises(cv_parser.NoTextExtractedError):
        _parse("scan.pdf", "application/pdf", make_empty_pdf())


def test_detect_content_type_by_extension_and_mime():
    assert cv_parser.detect_content_type("a.PDF", None) == "pdf"
    assert cv_parser.detect_content_type("a.docx", None) == "docx"
    assert cv_parser.detect_content_type("noext", "application/pdf") == "pdf"
    assert cv_parser.detect_content_type("a.txt", "text/plain") is None


def test_language_unknown_when_no_stopwords():
    assert cv_parser.detect_language("xyz 123 qwsz") == "unknown"
