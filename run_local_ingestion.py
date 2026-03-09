from __future__ import annotations

import argparse

from document_pipeline.services.local_pipeline import run_local_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover local deal documents, extract text, and write chunk artifacts."
    )
    parser.add_argument("deal_id", help="Deal folder name under data/documents/inbox/")
    parser.add_argument(
        "--chunk-chars",
        type=int,
        default=4000,
        help="Maximum characters per chunk before splitting page text.",
    )
    args = parser.parse_args()

    manifest = run_local_ingestion(args.deal_id, chunk_chars=args.chunk_chars)
    print(
        f"Processed deal {manifest['deal_id']}: "
        f"{manifest['document_count']} documents, {manifest['chunk_count']} chunks"
    )


if __name__ == "__main__":
    main()
