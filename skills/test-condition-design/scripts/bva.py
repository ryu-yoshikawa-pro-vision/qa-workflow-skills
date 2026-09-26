"""Generate exact two-value and three-value boundary targets."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import sys
from typing import Any

from runtime_contract import InvalidInput, canonical_decimal, canonicalize, ensure_list, ensure_nonempty_string, exact_add, post_process_targets, reject_unknown, run_cli, typed_value


SKILL = "test-condition-design"
GENERATOR = "bva"
GENERATOR_CONTRACT_VERSION = "bva-v1"
SCRIPT_PATH = Path(__file__).resolve()
THRESHOLD_TYPES = {"integer", "decimal", "date", "local_datetime", "fixed_offset_datetime"}
STEP_UNITS = {"integer", "decimal", "day", "second"}


def _typed(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name}はtyped valueである必要があります")
    normalized = typed_value(value)
    if normalized["type"] not in THRESHOLD_TYPES:
        raise InvalidInput(f"{name}のtypeがBVA対象外です")
    return normalized


def _step(value: Any, threshold_type: str, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"unit", "amount"}:
        raise InvalidInput(f"{name}が不正です")
    unit = value["unit"]
    amount = value["amount"]
    expected = {"integer": "integer", "decimal": "decimal", "date": "day", "local_datetime": "second", "fixed_offset_datetime": "second"}[threshold_type]
    if unit != expected:
        raise InvalidInput(f"{name}.unitがthreshold typeと不一致です")
    if unit in {"integer", "day", "second"}:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise InvalidInput(f"{name}.amountが不正です")
        normalized_amount: int | str = amount
    else:
        if not isinstance(amount, str):
            raise InvalidInput(f"{name}.amountが不正です")
        normalized_amount = canonical_decimal(amount)
        if normalized_amount == "0" or normalized_amount.startswith("-"):
            raise InvalidInput(f"{name}.amountは正である必要があります")
    return {"unit": unit, "amount": normalized_amount}


def _shift(threshold: dict[str, Any], step: dict[str, Any], direction: int) -> dict[str, Any]:
    kind = threshold["type"]
    raw = threshold["value"]
    amount = step["amount"]
    if kind == "integer":
        return {"type": kind, "value": raw + direction * amount}
    if kind == "decimal":
        delta = amount if direction > 0 else ("-" + amount)
        return {"type": kind, "value": exact_add(raw, delta)}
    if kind == "date":
        try:
            result = date.fromisoformat(raw) + timedelta(days=direction * amount)
        except (OverflowError, ValueError) as exc:
            raise InvalidInput("date BVA演算が表現不能です") from exc
        return {"type": kind, "value": result.isoformat()}
    try:
        parsed = datetime.fromisoformat(raw)
        if isinstance(amount, int):
            seconds = amount
        else:
            seconds = float(amount)
        result = parsed + timedelta(seconds=direction * seconds)
    except (OverflowError, ValueError) as exc:
        raise InvalidInput("datetime BVA演算が表現不能です") from exc
    if kind == "local_datetime" and result.tzinfo is not None:
        raise InvalidInput("local datetimeのoffsetが不正です")
    if kind == "fixed_offset_datetime" and result.tzinfo is None:
        raise InvalidInput("fixed offset datetimeのoffsetがありません")
    return {"type": kind, "value": result.isoformat(timespec="seconds")}


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "bva" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("bvaのruntime metadataが不正です")
    reject_unknown(input_value, {"boundaries"})
    targets: list[dict[str, Any]] = []
    boundaries = ensure_list(input_value["boundaries"], "boundaries")
    if not boundaries:
        raise InvalidInput("boundariesは1件以上必要です")
    seen: set[str] = set()
    for index, row in enumerate(boundaries):
        if not isinstance(row, dict):
            raise InvalidInput(f"boundaries[{index}]が不正です")
        required = {"boundary_key", "label", "side", "threshold", "inclusive", "step", "mode", "coverage_selection_reason", "authority_refs"}
        reject_unknown(row, required)
        key = ensure_nonempty_string(row["boundary_key"], f"boundaries[{index}].boundary_key")
        if key in seen:
            raise InvalidInput("boundary_keyが重複しています")
        seen.add(key)
        label = ensure_nonempty_string(row["label"], f"boundaries[{index}].label")
        if row["side"] not in {"lower", "upper"} or not isinstance(row["inclusive"], bool) or row["mode"] not in {"2-value", "3-value"}:
            raise InvalidInput("boundary metadataが不正です")
        reason = row["coverage_selection_reason"]
        if not isinstance(reason, str) or (row["mode"] == "3-value" and not reason):
            raise InvalidInput("coverage_selection_reasonが不正です")
        if not isinstance(row["authority_refs"], list) or len(set(row["authority_refs"])) != len(row["authority_refs"]) or not all(isinstance(value, str) and value for value in row["authority_refs"]):
            raise InvalidInput("boundary authority_refsが不正です")
        threshold = _typed(row["threshold"], f"boundaries[{index}].threshold")
        step = _step(row["step"], threshold["type"], f"boundaries[{index}].step")
        at = threshold
        if row["mode"] == "3-value":
            positions = [("BELOW", _shift(threshold, step, -1)), ("AT", at), ("ABOVE", _shift(threshold, step, 1))]
        else:
            other_direction = -1 if (row["side"] == "lower" and row["inclusive"]) or (row["side"] == "upper" and not row["inclusive"]) else 1
            positions = [("AT", at), ("OTHER", _shift(threshold, step, other_direction))]
        for position, value in positions:
            target_key = f"bva:{key}:{position}"
            execution = {
                "boundary": {"boundary_key": key, "label": label, "side": row["side"], "threshold": threshold, "inclusive": row["inclusive"], "step": step, "authority_refs": row["authority_refs"]},
                "position": position,
                "value": value,
            }
            targets.append({"target_key": target_key, "boundary_key": key, "boundary_label": label, "position": position, "value": value, "authority_refs": row["authority_refs"], "materializable": True, "execution": execution})
    processed = post_process_targets(metadata["model_key"], sorted(targets, key=lambda row: row["target_key"]))
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True,
        "payload": {"targets": processed, "coverage_summary": {"criterion": "boundary-values", "required": len(processed), "covered": len(processed), "complete": bool(processed)}, "metadata": {"coverage_mode": "2-value-or-3-value"}},
        "issues": [],
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
