from __future__ import annotations

from schemas import EXTRACTION_SCHEMA


def build_extraction_prompt(document_text: str) -> str:
    return f"""
You are helping build a valuation model from a corporate finance case packet or company filing.

Extract the following fields and return ONLY valid JSON with exactly these keys:
{EXTRACTION_SCHEMA}

Rules:
- Use numbers, not strings, for numeric values.
- Use decimals for percentages (example: 0.05 for 5%).
- If a field is missing, make a reasonable estimate and keep it conservative.
- Keep business_summary to 2-4 sentences.
- Do not include markdown fences.
- Do not add extra keys.

Document text:
{document_text}
""".strip()
