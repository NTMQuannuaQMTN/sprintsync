"""Execution-based tests for PDF/DOCX text extraction
(src/services/document_parser.py).

Builds real documents in memory and feeds their bytes through extract_text
— no mocking. DOCX uses python-docx (already a dependency). PDF uses a
hand-built minimal-but-valid PDF (raw object/xref/trailer structure written
directly) rather than adding a PDF-generation dependency (reportlab/fpdf)
purely for testing, which this project's conventions avoid — this exercises
the exact same PyPDF2.PdfReader code path extract_text uses in production
against a real, structurally valid PDF file.
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


def _make_minimal_pdf_bytes(text: str) -> bytes:
    """Builds a minimal, structurally valid single-page PDF (correct
    object offsets in the xref table) containing one text-drawing
    operator. Real bytes a real PDF reader can parse — not a mock."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode("latin-1")
    objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode())
        out.write(obj)
        out.write(b"\nendobj\n")
    xref_offset = out.tell()
    n = len(objects) + 1
    out.write(f"xref\n0 {n}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(b"trailer\n")
    out.write(f"<< /Size {n} /Root 1 0 R >>\n".encode())
    out.write(b"startxref\n")
    out.write(f"{xref_offset}\n".encode())
    out.write(b"%%EOF")
    return out.getvalue()


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


async def test_extract_text_from_real_pdf():
    pdf_bytes = _make_minimal_pdf_bytes("Implement GitHub OAuth login")
    text, error = await extract_text(pdf_bytes, "application/pdf", "spec.pdf")
    assert error == ""
    assert "Implement GitHub OAuth login" in text


async def test_extract_text_from_pdf_feeds_ai_extraction():
    """End-to-end: real PDF bytes -> real PyPDF2 extraction -> real AI task extraction."""
    from src.services.ai import ai_service

    pdf_bytes = _make_minimal_pdf_bytes("Implement webhook signature verification")
    text, error = await extract_text(pdf_bytes, "application/pdf", "spec.pdf")
    assert error == ""
    tasks = await ai_service.extract_tasks_from_text(text, "sprintsync")
    titles = [t.title for t in tasks]
    assert any("webhook signature verification" in t for t in titles)


async def test_reflow_recovers_lines_from_pypdf2_word_per_line_fragmentation():
    """Regression for a real user upload: PyPDF2 extracted this Vietnamese PDF
    with one word per line (a single blank line as the word-gap artifact,
    two-or-more blank lines marking a genuine line break) — verbatim
    excerpt of the actual `extracted_text` pulled from the database for
    that upload. Every line-anchored heuristic in ai.py saw single words
    and matched nothing, silently falling back to the generic task."""
    from src.services.document_parser import _reflow_fragmented_pdf_text

    fragmented = (
        "Cần\n \ncó\n \ntính\n \nnăng\n \ntạo\n \nmục\n \nđể\n \nquản\n \nlý\n \ncho\n \ndễ.\n"
        " \n \n \n"
        "Up\n \nlại\n \nảnh\n \n2\n \nbọn\n \nt\n"
    )
    reflowed = _reflow_fragmented_pdf_text(fragmented)
    lines = reflowed.split("\n")
    assert lines[0] == "Cần có tính năng tạo mục để quản lý cho dễ."
    assert lines[1] == "Up lại ảnh 2 bọn t"


async def test_extract_text_detects_pdf_by_extension_without_mime_type():
    """upload_spec's MIME check has a filename-extension fallback
    (specs.py's ALLOWED_MIME_TYPES check) — extract_text should route on
    the filename too, not just mime_type, matching that."""
    pdf_bytes = _make_minimal_pdf_bytes("Hello")
    text, error = await extract_text(pdf_bytes, "application/octet-stream", "spec.pdf")
    assert error == ""
    assert "Hello" in text
