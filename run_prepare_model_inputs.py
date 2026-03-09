from __future__ import annotations

import argparse

from document_pipeline.services.prepare_model_inputs import prepare_model_inputs_for_deal


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare workbook-ready model inputs and frontend review payload from resolved fields."
    )
    parser.add_argument("deal_id", help="Deal id that already has resolved fields.")
    args = parser.parse_args()

    result = prepare_model_inputs_for_deal(args.deal_id)
    print(f"Prepared {result['field_count']} review fields for {result['deal_id']}")
    print(f"Model input: {result['model_input_path']}")
    print(f"Review payload: {result['review_path']}")


if __name__ == "__main__":
    main()
