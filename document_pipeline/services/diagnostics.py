from __future__ import annotations

from typing import Any, Dict, List


def build_model_diagnostics(
    extracted: Dict[str, Any],
    dcf_info: Dict[str, Any] | None = None,
    lbo_info: Dict[str, Any] | None = None,
    checks: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    dcf_info = dcf_info or {}
    lbo_info = lbo_info or {}
    checks = checks or {}

    diagnostics: List[Dict[str, Any]] = []

    revenue = _num(extracted.get("revenue"))
    ebitda = _num(extracted.get("ebitda"))
    shares = _num(extracted.get("shares_outstanding"))
    debt = _num(extracted.get("debt"))
    cash = _num(extracted.get("cash"))
    entry_multiple = _num(extracted.get("entry_multiple"))
    exit_multiple = _num(extracted.get("exit_multiple"))
    entry_year = _num(extracted.get("entry_year"))
    share_price = _num(dcf_info.get("share_price_multiple"))
    equity_value = _num(dcf_info.get("equity_value_multiple"))
    enterprise_value = _num(dcf_info.get("enterprise_value_multiple"))
    revolver_limit = _num(extracted.get("revolver_limit"))
    exit_debt = _num(lbo_info.get("exit_debt"))

    if revenue <= 0:
        diagnostics.append(
            _issue(
                severity="high",
                title="Revenue is zero or missing",
                explanation="The model is using zero or non-positive revenue, which will distort margins, growth, leverage, and valuation outputs.",
                likely_causes=[
                    "No explicit annual revenue was extracted from the uploaded documents.",
                    "Revenue may be labeled as sales, net sales, or total revenue rather than revenue.",
                    "The extracted value may have been skipped or overridden incorrectly.",
                ],
                suggested_actions=[
                    "Override revenue on the review screen with the latest annual or LTM sales figure.",
                    "Check the uploaded filing for labels like sales, net sales, or total revenue.",
                    "Update the value later in the Excel workbook on the historicals_input tab if needed.",
                ],
            )
        )

    if ebitda <= 0:
        diagnostics.append(
            _issue(
                severity="high",
                title="EBITDA is zero or missing",
                explanation="A non-positive EBITDA makes leverage, returns, and valuation outputs much less reliable.",
                likely_causes=[
                    "The document did not explicitly state EBITDA or adjusted EBITDA.",
                    "The model relied on a weak estimate path or no estimate was accepted.",
                ],
                suggested_actions=[
                    "Override EBITDA directly if you know the latest annual or LTM value.",
                    "Provide revenue and an EBITDA margin so the model can derive EBITDA more credibly.",
                    "Adjust the Excel workbook assumptions if the extracted figure is not representative.",
                ],
            )
        )

    if shares <= 1:
        diagnostics.append(
            _issue(
                severity="high",
                title="Shares outstanding looks like a placeholder",
                explanation="Per-share outputs are likely unreliable because the share count is missing or set to a placeholder value.",
                likely_causes=[
                    "No clear common shares outstanding figure was extracted.",
                    "The model fell back to a divide-by-zero guard instead of a real share count.",
                ],
                suggested_actions=[
                    "Override shares outstanding with the latest basic or common shares outstanding figure.",
                    "Use the review page source links or web fallback sources to confirm the correct share count.",
                    "You can also update the share count later in the Excel workbook.",
                ],
            )
        )

    if share_price < 0:
        diagnostics.append(
            _issue(
                severity="high",
                title="Implied share price is negative",
                explanation="The model is producing a negative implied share price, which usually means implied equity value is below zero.",
                likely_causes=[
                    "Net debt is too high relative to implied enterprise value.",
                    "Revenue, EBITDA, or valuation multiples are too low or missing.",
                    "Shares outstanding or debt inputs may be incorrect.",
                ],
                suggested_actions=[
                    "Review revenue, EBITDA, debt, and share count on the review page.",
                    "Try overriding the entry or exit multiple with a more realistic value.",
                    "Open the Excel workbook and inspect debt sizing, valuation assumptions, and share count directly.",
                ],
            )
        )

    if entry_multiple <= 0 or exit_multiple <= 0:
        diagnostics.append(
            _issue(
                severity="medium",
                title="Valuation multiple input is weak",
                explanation="One or more valuation multiples are missing or non-positive, so valuation may rely on low-confidence defaults or estimates.",
                likely_causes=[
                    "The uploaded documents did not include explicit comps or transaction multiple data.",
                    "The multiple was estimated from fallback logic rather than extracted directly.",
                ],
                suggested_actions=[
                    "Override entry and exit multiples on the review page.",
                    "Upload a comps or analyst note document if you want the model to infer multiples from public data.",
                ],
            )
        )

    if debt > 0 and ebitda > 0 and debt / max(ebitda, 1.0) > 10:
        diagnostics.append(
            _issue(
                severity="medium",
                title="Entry leverage looks very high",
                explanation="Debt relative to EBITDA is unusually high and may cause stressed or unrealistic LBO outputs.",
                likely_causes=[
                    "Debt may include items that should not be treated as acquisition debt.",
                    "EBITDA may be understated or missing while debt is populated.",
                ],
                suggested_actions=[
                    "Review debt and EBITDA inputs on the review page.",
                    "Use the debt-free acquisition toggle if the target should be treated as debt free.",
                ],
            )
        )

    if revolver_limit > 0 and exit_debt > 0 and checks.get("revolver_within_limit") is False:
        diagnostics.append(
            _issue(
                severity="medium",
                title="Revolver exceeds its limit",
                explanation="The debt schedule is drawing more revolver capacity than the configured limit allows.",
                likely_causes=[
                    "The revolver limit is too low for the case assumptions.",
                    "Cash generation or debt sizing is inconsistent with the operating model.",
                ],
                suggested_actions=[
                    "Increase the revolver limit or reduce debt sizing assumptions.",
                    "Inspect the debt_schedule and sources_uses tabs in Excel after download.",
                ],
            )
        )

    if entry_year < 2000:
        diagnostics.append(
            _issue(
                severity="low",
                title="Entry year may be wrong",
                explanation="The model is using an unusual entry year, which can mislabel historical and projection periods.",
                likely_causes=[
                    "Entry year was not extracted and a bad override/default was used.",
                ],
                suggested_actions=[
                    "Override entry year on the review page if the filing period is different.",
                ],
            )
        )

    summary = {
        "issue_count": len(diagnostics),
        "high_severity_count": sum(1 for item in diagnostics if item["severity"] == "high"),
        "diagnostics": diagnostics,
        "user_note": "You can override these inputs before analysis or adjust them later directly in the Excel workbook.",
    }
    return summary


def _issue(
    *,
    severity: str,
    title: str,
    explanation: str,
    likely_causes: List[str],
    suggested_actions: List[str],
) -> Dict[str, Any]:
    return {
        "severity": severity,
        "title": title,
        "explanation": explanation,
        "likely_causes": likely_causes,
        "suggested_actions": suggested_actions,
    }


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
