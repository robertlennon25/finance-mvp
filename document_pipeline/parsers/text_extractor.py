from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import fitz
import re
from html import unescape


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".html", ".htm"}


def is_supported_document(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def extract_document_payload(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_payload(path)
    if suffix in {".txt", ".md"}:
        return _extract_text_payload(path)
    if suffix in {".html", ".htm"}:
        return _extract_html_payload(path)
    raise ValueError(f"Unsupported document type: {path.suffix}")


def _extract_pdf_payload(path: Path) -> Dict[str, Any]:
    doc = fitz.open(path)
    pages: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        full_text_parts.append(text)
        pages.append(
            {
                "page_number": page_number,
                "text": text,
            }
        )

    return {
        "document_type": "pdf",
        "page_count": len(pages),
        "text": "\n\n".join(part for part in full_text_parts if part),
        "pages": pages,
    }


def _extract_text_payload(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    clean_text = text.strip()
    return {
        "document_type": "text",
        "page_count": 1,
        "text": clean_text,
        "pages": [
            {
                "page_number": 1,
                "text": clean_text,
            }
        ],
    }


def _extract_html_payload(path: Path) -> Dict[str, Any]:
    html = path.read_text(encoding="utf-8", errors="ignore")
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = unescape(text)
    clean_text = " ".join(text.split())
    return {
        "document_type": "html",
        "page_count": 1,
        "text": clean_text,
        "pages": [
            {
                "page_number": 1,
                "text": clean_text,
            }
        ],
    }
