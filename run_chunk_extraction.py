from __future__ import annotations

import argparse

from document_pipeline.services.openai_extraction import run_chunk_extraction


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read normalized chunks and extract field candidates with gpt-4.1-mini."
    )
    parser.add_argument("deal_id", help="Deal id that has already been ingested.")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name.")
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Optional cap for testing with a subset of chunks.",
    )
    args = parser.parse_args()

    result = run_chunk_extraction(
        deal_id=args.deal_id,
        model=args.model,
        max_chunks=args.max_chunks,
    )
    print(
        f"Extracted {result['candidate_count']} candidates for {result['deal_id']}"
    )
    if result.get("cached"):
        print("Cache hit: reused prior extraction artifacts")
    print(f"Raw output: {result['raw_output_path']}")
    print(f"Normalized candidates: {result['normalized_path']}")


if __name__ == "__main__":
    main()
