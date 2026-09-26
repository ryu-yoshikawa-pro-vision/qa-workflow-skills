"""Reproducible Random Testing using the fixed pcg32-v1 contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime_contract import (
    InvalidInput,
    canonical_json_text,
    ensure_int,
    ensure_list,
    ensure_nonempty_string,
    post_process_targets,
    reject_unknown,
    run_cli,
    typed_sort_key,
    typed_value,
)


SKILL = "test-condition-design"
GENERATOR = "random_testing"
GENERATOR_CONTRACT_VERSION = "random-testing-v1"
SCRIPT_PATH = Path(__file__).resolve()
UINT32_BOUND = 1 << 32
UINT64_MASK = (1 << 64) - 1
PCG_MULTIPLIER = 6364136223846793005
PCG_INCREMENT = 109


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


class Pcg32:
    """PCG XSH RR 64/32 with the plan's fixed stream initialization."""

    def __init__(self, seed: int) -> None:
        self.state = 0
        self._advance()
        self.state = (self.state + seed) & UINT64_MASK
        self._advance()

    def _advance(self) -> int:
        old = self.state
        self.state = (old * PCG_MULTIPLIER + PCG_INCREMENT) & UINT64_MASK
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rotation = old >> 59
        return ((xorshifted >> rotation) | (xorshifted << ((-rotation) & 31))) & 0xFFFFFFFF

    def next_uint32(self) -> int:
        return self._advance()

    def bounded_uint32(self, bound: int) -> int:
        if bound < 1 or bound > UINT32_BOUND:
            raise InvalidInput("PRNG boundが不正です")
        threshold = ((UINT32_BOUND - bound) % bound)
        while True:
            raw = self.next_uint32()
            if raw >= threshold:
                return raw % bound


def _normalize_distribution(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or "type" not in value:
        raise InvalidInput("distributionが不正です")
    distribution_type = value["type"]
    if distribution_type == "uniform_finite":
        reject_unknown(value, {"type", "values"})
        values = ensure_list(value["values"], "distribution.values")
        if not values:
            raise InvalidInput("uniform_finite valuesは1件以上必要です")
        normalized = [typed_value(item) for item in values]
        if len({canonical_json_text(item) for item in normalized}) != len(normalized):
            raise InvalidInput("uniform_finite valuesが重複しています")
        return {"type": distribution_type, "values": normalized}
    if distribution_type == "uniform_integer":
        reject_unknown(value, {"type", "minimum", "maximum"})
        minimum = ensure_int(value["minimum"], "distribution.minimum")
        maximum = ensure_int(value["maximum"], "distribution.maximum")
        if minimum > maximum or maximum - minimum + 1 > UINT32_BOUND:
            raise InvalidInput("uniform_integerの範囲が不正です")
        return {"type": distribution_type, "minimum": minimum, "maximum": maximum}
    if distribution_type == "categorical":
        reject_unknown(value, {"type", "entries"})
        entries_raw = ensure_list(value["entries"], "distribution.entries")
        if not entries_raw:
            raise InvalidInput("categorical entriesは1件以上必要です")
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        total = 0
        for entry in entries_raw:
            if not isinstance(entry, dict):
                raise InvalidInput("categorical entryが不正です")
            reject_unknown(entry, {"value", "weight"})
            item = typed_value(entry["value"])
            item_key = canonical_json_text(item)
            if item_key in seen:
                raise InvalidInput("categorical valueが重複しています")
            seen.add(item_key)
            weight = ensure_int(entry["weight"], "categorical weight", minimum=1, maximum=2_147_483_647)
            total += weight
            if total > UINT32_BOUND:
                raise InvalidInput("categorical weight合計が大きすぎます")
            entries.append({"value": item, "weight": weight})
        return {"type": distribution_type, "entries": entries, "total_weight": total}
    raise InvalidInput("distribution.typeが不正です")


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "random" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("Random Testingのruntime metadataが不正です")
    reject_unknown(input_value, {"input_label", "seed", "case_count", "distribution"}, {"authority_refs", "reference_refs"})
    input_label = ensure_nonempty_string(input_value["input_label"], "input_label")
    seed = ensure_int(input_value["seed"], "seed", minimum=0, maximum=UINT64_MASK)
    case_count = ensure_int(input_value["case_count"], "case_count", minimum=1, maximum=10_000)
    distribution = _normalize_distribution(input_value["distribution"])
    authority_refs = _refs(input_value.get("authority_refs", []), "authority_refs")
    reference_refs = _refs(input_value.get("reference_refs", []), "reference_refs")
    prng = Pcg32(seed)
    cases: list[dict[str, Any]] = []
    for index in range(1, case_count + 1):
        if distribution["type"] == "uniform_finite":
            value = distribution["values"][prng.bounded_uint32(len(distribution["values"]))]
        elif distribution["type"] == "uniform_integer":
            value = prng.bounded_uint32(distribution["maximum"] - distribution["minimum"] + 1) + distribution["minimum"]
            value = {"type": "integer", "value": value}
        else:
            draw = prng.bounded_uint32(distribution["total_weight"])
            cumulative = 0
            value = None
            for entry in distribution["entries"]:
                cumulative += entry["weight"]
                if draw < cumulative:
                    value = entry["value"]
                    break
            if value is None:  # pragma: no cover - guarded by total_weight
                raise InvalidInput("categorical drawを解決できません")
        target_key = f"random:case:{index:06d}"
        execution = {"input_label": input_label, "case_index": index, "value": value, "seed": seed, "distribution": distribution}
        cases.append({"target_key": target_key, "case_index": index, "input_label": input_label, "value": value, "materializable": True, "execution": execution, "authority_refs": authority_refs, "reference_refs": reference_refs})
    targets = post_process_targets(metadata["model_key"], cases)
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True,
        "payload": {"input_label": input_label, "seed": seed, "case_count": case_count, "distribution": distribution, "targets": targets, "completion_summary": {"required_case_count": case_count, "generated_case_count": len(targets), "complete": len(targets) == case_count}, "authority_refs": authority_refs, "reference_refs": reference_refs},
        "issues": [],
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
