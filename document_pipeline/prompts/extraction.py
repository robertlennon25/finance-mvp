from __future__ import annotations

from document_pipeline.schemas import EXTRACTED_FIELD_SCHEMA

EXTRACTION_PROMPT_VERSION = "2026-03-09-v2"


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
- Prefer annual/LTM values when multiple periods appear.
- Use equivalent labels when they are clearly the same concept:
  - revenue may appear as sales, net sales, net revenue, total revenue
  - debt may appear as long-term debt, total debt, total borrowings
  - cash may appear as cash and cash equivalents
  - shares outstanding may appear as common shares outstanding
- If a value can be computed directly from figures stated in the same chunk, include it and explain the derivation in `notes`.
- Do not invent values that are not grounded in the chunk.
- Use decimals for percentages when possible.
- Use plain numbers for numeric values.
- `confidence` must be between 0 and 1.
- `method` may be `extracted` or `inferred_from_chunk`.
- Keep `notes` short.
- Do not include markdown fences.

Document chunk:
{chunk_text}
""".strip()


def build_document_synthesis_prompt(context_snippets: list[dict[str, str]], missing_fields: list[str]) -> str:
    return f"""
You are reviewing multiple important finance-document snippets to fill missing LBO model inputs.

Return ONLY valid JSON:
{{
  "candidates": [
    {{
      "field_name": "revenue",
      "value": 123,
      "confidence": 0.0,
      "source_locator": "doc page x",
      "method": "inferred_from_document",
      "notes": "short explanation of how this was inferred"
    }}
  ]
}}

Allowed field names:
{["revenue", "ebitda", "shares_outstanding", "cash", "debt", "entry_multiple", "exit_multiple", "ebitda_margin_assumption"]}

Rules:
- Only return fields that are supported by the snippets.
- Use reasonable finance reasoning across snippets when the exact label differs.
- Revenue may appear as sales, net sales, net revenue, total revenue, segment revenue, or implied by margin tables.
- EBITDA may be adjusted EBITDA, EBITDA, or derivable from revenue and margin if both are clearly supported.
- Shares outstanding may come from cover pages, balance sheet/share tables, or clearly labeled public-company statistics.
- If you infer a value, explain the derivation in `notes`.
- Prefer the most recent annual/LTM value.
- `method` must be `inferred_from_document`.
- Do not include markdown fences.

Missing fields:
{missing_fields}

Relevant snippets:
{context_snippets}
""".strip()
