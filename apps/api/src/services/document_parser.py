"""Document parser — extract text from PDF and DOCX files."""
import io
from typing import Tuple


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


async def _parse_pdf(file_bytes: bytes) -> Tuple[str, str]:
    try:
        import PyPDF2  # type: ignore

        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
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
