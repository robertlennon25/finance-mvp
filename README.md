# Finance AI MVP

Local MVP pipeline:

1. Extract text from one PDF
2. Send text to an LLM for structured JSON extraction
3. Build a simple valuation model
4. Export an Excel workbook

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your API key:

```bash
export OPENAI_API_KEY="your_key_here"
```

## Run

```bash
python3 main.py /path/to/document.pdf
```

Output workbook is written to `outputs/valuation_model.xlsx`.

## Notes

- This is intentionally scoped for a quick local MVP.
- The extraction schema is narrow and editable in `schemas.py`.
- The model call is isolated in `model_client.py` so it can be swapped later.
