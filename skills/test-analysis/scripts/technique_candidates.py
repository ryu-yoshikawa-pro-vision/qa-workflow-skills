"""Map normalized test-analysis signals to deterministic technique candidates."""

from __future__ import annotations

from pathlib import Path
import sys

from runtime_contract import InvalidInput, ensure_key, reject_unknown, run_cli


SKILL = "test-analysis"
GENERATOR = "technique_candidates"
GENERATOR_CONTRACT_VERSION = "technique-candidates-v1"
SCRIPT_PATH = Path(__file__).resolve()
SIGNALS = [
    "ordered_domain", "explicit_boundaries", "equivalence_classes", "multiple_discrete_conditions", "stateful", "multiple_factors",
    "explicit_flow", "multi_variable_domain", "crud_model", "operational_profile", "metamorphic_relation", "grammar_model",
]
CANDIDATES = [
    ("ordered_domain", "境界値分析"), ("explicit_boundaries", "境界値分析"), ("equivalence_classes", "同値分割"),
    ("multiple_discrete_conditions", "デシジョンテーブル"), ("stateful", "状態遷移"), ("multiple_factors", "Pairwise / 組合せ"),
    ("explicit_flow", "シナリオ / ユースケース"), ("multi_variable_domain", "Domain Testing"), ("crud_model", "CRUD Testing"),
    ("operational_profile", "Random Testing"), ("metamorphic_relation", "Metamorphic Testing"), ("grammar_model", "Syntax-Based Testing"),
]


def generate(input_value: dict, metadata: dict) -> dict:
    selection_key = ensure_key(input_value.get("selection_key"), "selection_key")
    if metadata["runtime_unit_key"] != f"artifact:technique_candidates:{selection_key}":
        raise InvalidInput("technique_candidates runtime unitがselection_keyと不一致です")
    reject_unknown(input_value, {"selection_key", "signals"})
    signals = input_value["signals"]
    if not isinstance(signals, dict) or set(signals) != set(SIGNALS):
        raise InvalidInput("signalsのkey集合が不正です")
    if any(value not in {True, False, None} for value in signals.values()):
        raise InvalidInput("signal valueが不正です")
    candidates = []
    for signal, candidate in CANDIDATES:
        if signals[signal] is True and candidate not in candidates:
            candidates.append(candidate)
    undetermined = [signal for signal in SIGNALS if signals[signal] is None]
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"selection_key": selection_key, "candidates": candidates, "undetermined_signals": undetermined, "complete": not undetermined}, "issues": []}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
