from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from openpyxl import Workbook


@dataclass
class ModelContext:
    wb: Workbook
    model_inputs: Dict[str, Any]
    extracted: Dict[str, Any]
    assumptions: Any
    python_output: Dict[str, Any]
    refs: Dict[str, str] = field(default_factory=dict)

    def set_ref(self, key: str, sheet_name: str, cell: str) -> str:
        ref = f"'{sheet_name}'!${cell}"
        self.refs[key] = ref
        return ref

    def ref(self, key: str) -> str:
        try:
            return self.refs[key]
        except KeyError as exc:
            raise KeyError(f"Missing workbook reference: {key}") from exc
