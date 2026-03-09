from __future__ import annotations

from pathlib import Path

import fitz


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract raw text from a PDF using PyMuPDF."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(path)
    parts: list[str] = []
    for page in doc:
        parts.append(page.get_text())
    return "\n".join(parts)


def get_relevant_text(text: str, max_chars: int = 14000) -> str:
    """Small MVP helper: just trim the document for prompt size control."""
    cleaned = " ".join(text.split())
    return cleaned[:max_chars]
