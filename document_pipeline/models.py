from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentRecord:
    deal_id: str
    document_id: str
    filename: str
    path: str
    document_type: str = "unknown"
    file_size: int = 0
    sha256: str = ""


@dataclass
class ChunkRecord:
    document_id: str
    chunk_id: str
    chunk_index: int
    text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldCandidate:
    field_name: str
    value: Any
    confidence: float
    source_document_id: str
    source_locator: str
    method: str
    notes: str = ""
    source_urls: List[str] = field(default_factory=list)


@dataclass
class ResolvedField:
    field_name: str
    value: Any
    resolution_method: str
    source_document_id: Optional[str] = None
    source_locator: str = ""


@dataclass
class ExtractionBundle:
    deal_id: str
    documents: List[DocumentRecord]
    chunks: List[ChunkRecord]
    candidates: List[FieldCandidate]
    resolved_fields: List[ResolvedField]
