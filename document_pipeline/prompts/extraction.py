from __future__ import annotations

from document_pipeline.schemas import EXTRACTED_FIELD_SCHEMA

EXTRACTION_PROMPT_VERSION = "2026-03-09-v1"


def build_chunk_extraction_prompt(chunk_text: str, source_locator: str) -> str:
    return f"""
You are extracting valuation-model inputs from a corporate finance document chunk.

Return ONLY valid JSON with this structure:
{{
  "candidates": [
    {{
      "field_name": "one key from the allowed fields",
      "value": "number, string, object, or array depending on the field",
      "confidence": 0.0,
      "source_locator": "{source_locator}",
      "method": "extracted",
      "notes": "short note"
    }}
  ]
}}

Allowed field names:
{list(EXTRACTED_FIELD_SCHEMA.keys())}

Rules:
- Only include fields that are explicitly stated or strongly implied in the chunk.
- Do not invent values for fields not supported by the chunk.
- Use decimals for percentages when possible.
- Use plain numbers for numeric values.
- `confidence` must be between 0 and 1.
- `method` must be `extracted`.
- Keep `notes` short.
- Do not include markdown fences.

Document chunk:
{chunk_text}
""".strip()
