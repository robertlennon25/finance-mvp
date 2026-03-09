from __future__ import annotations

import argparse

from document_pipeline.services.resolve_fields import resolve_deal_fields


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve extracted field candidates into final deal inputs, applying overrides when present."
    )
    parser.add_argument("deal_id", help="Deal id that already has extracted field candidates.")
    args = parser.parse_args()

    result = resolve_deal_fields(args.deal_id)
    print(
        f"Resolved {result['resolved_field_count']} fields for {result['deal_id']} "
        f"with {result['override_count']} overrides"
    )
    print(f"Resolved fields: {result['resolved_path']}")


if __name__ == "__main__":
    main()
