"""Document parser — extract text from PDF and DOCX files."""
import io
import re
from typing import List, Tuple

import httpx

_GOOGLE_DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


async def extract_google_doc_text(url: str) -> Tuple[str, str]:
    """Fetch a Google Doc's plain-text export by URL.

    No OAuth/service-account flow — this only works for docs shared as
    "Anyone with the link" (Viewer). A restricted doc's export redirects to
    a Google sign-in page instead of the document; that's detected via the
    response content-type (an HTML login page, not text/plain) and reported
    as a clear error rather than silently ingesting the login page as if it
    were the spec's content.
    """
    match = _GOOGLE_DOC_ID_RE.search(url)
    if not match:
        return "", "That doesn't look like a Google Docs link (expected a docs.google.com/document/d/... URL)."

    doc_id = match.group(1)
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(export_url)
    except Exception as e:
        return "", f"Could not reach Google Docs: {e}"

    content_type = resp.headers.get("content-type", "")
    if resp.status_code != 200 or "text/plain" not in content_type:
        return (
            "",
            "Could not access this Google Doc. Make sure it's shared as "
            '"Anyone with the link" (Viewer) — restricted documents can\'t be read.',
        )

    text = resp.content.decode("utf-8", errors="replace")
    if not text.strip():
        return "", "The Google Doc appears to be empty."
    return text, ""


async def extract_text(file_bytes: bytes, mime_type: str, filename: str) -> Tuple[str, str]:
    """
    Extract text from uploaded document.
    Returns (extracted_text, error_message).
    """
    try:
        if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
            return await _parse_pdf(file_bytes)
        elif mime_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ) or filename.lower().endswith(".docx"):
            return await _parse_docx(file_bytes)
        else:
            return "", f"Unsupported file type: {mime_type}"
    except Exception as e:
        return "", str(e)


def _reflow_fragmented_pdf_text(text: str) -> str:
    """PyPDF2's extract_text() sometimes emits one *word* per line instead of
    one visual line per line — seen in practice on a real Vietnamese PDF
    where each glyph run got its own text-positioning operator. That
    fragmentation defeats every line-anchored heuristic downstream (each
    "line" is a single word).

    A single blank line between two words is that fragmentation's word-gap
    artifact; two or more blank lines is a genuine line/paragraph break in
    the source PDF (verified against the real extracted text — a title
    line was followed by 3-5 blank lines before the next real heading, while
    words within one line were separated by exactly one blank line). Zero
    blank lines between two already-multi-word tokens means extract_text()
    didn't fragment this file at all, so those stay on separate lines,
    unchanged from today's behavior.
    """
    tokens = text.split("\n")
    lines: List[str] = []
    current: List[str] = []
    blank_run = 0
    for tok in tokens:
        if tok.strip() == "":
            blank_run += 1
            continue
        if current and blank_run == 1:
            current.append(tok.strip())
        else:
            if current:
                lines.append(" ".join(current))
            current = [tok.strip()]
        blank_run = 0
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


async def _parse_pdf(file_bytes: bytes) -> Tuple[str, str]:
    try:
        import PyPDF2  # type: ignore

        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                texts.append(_reflow_fragmented_pdf_text(text))
        return "\n".join(texts), ""
    except ImportError:
        return "", "PyPDF2 not installed. Run: pip install PyPDF2"
    except Exception as e:
        return "", f"PDF parsing error: {e}"


async def _parse_docx(file_bytes: bytes) -> Tuple[str, str]:
    try:
        from docx import Document  # type: ignore

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs), ""
    except ImportError:
        return "", "python-docx not installed. Run: pip install python-docx"
    except Exception as e:
        return "", f"DOCX parsing error: {e}"
