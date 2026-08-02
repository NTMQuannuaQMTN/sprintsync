"""Execution-based test for DOCX text extraction (src/services/document_parser.py).

Builds a real .docx in memory with python-docx (already a project dependency)
and feeds its bytes through extract_text — no mocking. PDF extraction is not
covered here: generating a real PDF fixture would require adding a new
dependency (reportlab/fpdf) purely for testing, which this project's
conventions avoid; PDF extraction remains verified by manual code trace only
(see CHECKLIST.md SPEC-002).
"""
import io

from docx import Document

from src.services.document_parser import extract_text


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def test_extract_text_from_real_docx():
    docx_bytes = _make_docx_bytes([
        "Project Specification",
        "Implement GitHub OAuth login",
        "Build the dashboard overview page",
    ])
    text, error = await extract_text(
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "spec.docx",
    )
    assert error == ""
    assert "Implement GitHub OAuth login" in text
    assert "Build the dashboard overview page" in text


async def test_extract_text_from_docx_feeds_ai_extraction():
    """End-to-end: real DOCX bytes -> real text extraction -> real AI task extraction."""
    from src.services.ai import ai_service

    docx_bytes = _make_docx_bytes([
        "- Implement GitHub OAuth login",
        "- Add webhook signature verification",
    ])
    text, error = await extract_text(
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "spec.docx",
    )
    assert error == ""
    tasks = await ai_service.extract_tasks_from_text(text, "sprintsync")
    titles = [t.title for t in tasks]
    assert any("GitHub OAuth login" in t for t in titles)
    assert any("webhook signature verification" in t for t in titles)


async def test_extract_text_unsupported_type_returns_error():
    text, error = await extract_text(b"not a real document", "text/plain", "notes.txt")
    assert text == ""
    assert "Unsupported file type" in error
