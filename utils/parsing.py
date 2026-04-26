"""Parse uploaded resumes (PDF or plain text) into a string we can feed the LLM."""

from __future__ import annotations

import io


def extract_resume_text(uploaded_file) -> str:
    """
    `uploaded_file` is a Streamlit UploadedFile. Returns plain text.
    Supports PDF, TXT, and Markdown.
    """
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()
    raw = uploaded_file.read()

    if name.endswith(".pdf"):
        return _extract_pdf(raw)
    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_pdf(data: bytes) -> str:
    """Extract text from a PDF using pypdf (pure-Python, no system deps)."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "pypdf is required for PDF parsing. Run: pip install pypdf"
        ) from exc

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n".join(pages).strip()