"""Generate shortest deterministic leftmost grammar cases and explicit mutations."""

from __future__ import annotations

import hashlib
import heapq
from pathlib import Path
from typing import Any

from runtime_contract import (
    InvalidInput,
    LimitExceeded,
    MAX_EXPLORATION_NODES,
    canonical_json_bytes,
    canonicalize,
    ensure_int,
    ensure_key,
    ensure_list,
    ensure_nonempty_string,
    post_process_targets,
    reject_unknown,
    run_cli,
)


SKILL = "test-condition-design"
GENERATOR = "grammar_cases"
GENERATOR_CONTRACT_VERSION = "grammar-cases-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _hash_component(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def _normalize(input_value: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]], int, list[dict[str, Any]]]:
    reject_unknown(input_value, {"input_label", "start", "productions", "max_depth", "mutations"})
    input_label = ensure_nonempty_string(input_value["input_label"], "input_label")
    start = ensure_nonempty_string(input_value["start"], "start")
    max_depth = ensure_int(input_value["max_depth"], "max_depth", minimum=1, maximum=64)
    production_rows = ensure_list(input_value["productions"], "productions")
    productions: list[dict[str, Any]] = []
    production_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(production_rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"productions[{index}]が不正です")
        reject_unknown(row, {"production_key", "lhs", "rhs"})
        production_key = ensure_key(row["production_key"], "production_key")
        if production_key in production_map:
            raise InvalidInput("production_keyが重複しています")
        lhs = ensure_nonempty_string(row["lhs"], "production lhs")
        rhs_raw = ensure_list(row["rhs"], "production rhs")
        rhs: list[dict[str, str]] = []
        for item in rhs_raw:
            if not isinstance(item, dict) or len(item) != 1 or ("terminal" not in item and "nonterminal" not in item):
                raise InvalidInput("production RHS itemが不正です")
            if "terminal" in item:
                if not isinstance(item["terminal"], str):
                    raise InvalidInput("terminalはstringである必要があります")
                rhs.append({"terminal": item["terminal"]})
            else:
                rhs.append({"nonterminal": ensure_nonempty_string(item["nonterminal"], "nonterminal")})
        normalized = {"production_key": production_key, "lhs": lhs, "rhs": rhs}
        production_map[production_key] = normalized
        productions.append(normalized)
    if not productions:
        raise InvalidInput("productionsは1件以上必要です")
    if start not in {row["lhs"] for row in productions}:
        raise InvalidInput("start symbolにproductionがありません")
    productions.sort(key=lambda row: row["production_key"])

    mutations_raw = ensure_list(input_value["mutations"], "mutations")
    mutations: list[dict[str, Any]] = []
    mutation_keys: set[str] = set()
    for index, row in enumerate(mutations_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"mutations[{index}]が不正です")
        if not {"mutation_key", "op", "production_key", "symbol_index"}.issubset(row):
            raise InvalidInput("mutation必須fieldがありません")
        mutation_key = ensure_key(row["mutation_key"], "mutation_key")
        if mutation_key in mutation_keys:
            raise InvalidInput("mutation_keyが重複しています")
        mutation_keys.add(mutation_key)
        op = row["op"]
        if op == "delete_terminal":
            reject_unknown(row, {"mutation_key", "op", "production_key", "symbol_index"})
        elif op in {"replace_terminal", "insert_terminal"}:
            reject_unknown(row, {"mutation_key", "op", "production_key", "symbol_index", "value"})
            if not isinstance(row.get("value"), str) or not row["value"]:
                raise InvalidInput("mutation valueは非空stringである必要があります")
        else:
            raise InvalidInput("mutation opが不正です")
        production_key = ensure_key(row["production_key"], "mutation.production_key")
        if production_key not in production_map:
            raise InvalidInput("mutationがunknown productionを参照しています")
        symbol_index = ensure_int(row["symbol_index"], "mutation.symbol_index", minimum=0)
        if op != "insert_terminal" and symbol_index >= len(production_map[production_key]["rhs"]):
            raise InvalidInput("mutation symbol_indexが範囲外です")
        if op == "insert_terminal" and symbol_index > len(production_map[production_key]["rhs"]):
            raise InvalidInput("mutation insert symbol_indexが範囲外です")
        if op in {"delete_terminal", "replace_terminal"} and "nonterminal" in production_map[production_key]["rhs"][symbol_index]:
            raise InvalidInput("delete / replaceの対象はterminalである必要があります")
        normalized = {"mutation_key": mutation_key, "op": op, "production_key": production_key, "symbol_index": symbol_index}
        if op in {"replace_terminal", "insert_terminal"}:
            normalized["value"] = row["value"]
        mutations.append(normalized)
    mutations.sort(key=lambda row: row["mutation_key"])
    return input_label, start, productions, max_depth, mutations


def _rhs_items(rhs: list[dict[str, str]], depth: int) -> tuple[tuple[str, str, int], ...]:
    return tuple(("T", item["terminal"], depth) if "terminal" in item else ("N", item["nonterminal"], depth) for item in rhs)


def _derive(productions: list[dict[str, Any]], start: str, max_depth: int, target_production: str) -> dict[str, Any] | None:
    production_map = {row["production_key"]: row for row in productions}
    initial = (("N", start, 0),)
    queue: list[tuple[int, tuple[str, ...], int, tuple[tuple[str, str, int], ...]]] = [(0, (), 0, initial)]
    best: dict[tuple[tuple[str, str, int], ...], tuple[int, tuple[str, ...]]] = {initial: (0, ())}
    serial = 0
    explored = 0
    while queue:
        steps, sequence, _serial, form = heapq.heappop(queue)
        explored += 1
        if explored > MAX_EXPLORATION_NODES:
            raise LimitExceeded("grammar derivation exploration nodeがhard limitを超えています")
        if all(item[0] == "T" for item in form):
            if target_production in sequence:
                return {"input_text": "".join(item[1] for item in form), "production_key_sequence": list(sequence)}
            continue
        first_nonterminal = next(index for index, item in enumerate(form) if item[0] == "N")
        symbol, lhs, depth = form[first_nonterminal]
        assert symbol == "N"
        for production in sorted(productions, key=lambda row: row["production_key"]):
            if production["lhs"] != lhs:
                continue
            child_depth = depth + 1
            if any("nonterminal" in item and child_depth > max_depth for item in production["rhs"]):
                continue
            replacement = _rhs_items(production["rhs"], child_depth)
            next_form = form[:first_nonterminal] + replacement + form[first_nonterminal + 1:]
            next_sequence = sequence + (production["production_key"],)
            score = (steps + 1, next_sequence)
            previous = best.get(next_form)
            if previous is not None and score >= previous:
                continue
            best[next_form] = score
            serial += 1
            heapq.heappush(queue, (steps + 1, next_sequence, serial, next_form))
    return None


def _mutated_productions(productions: list[dict[str, Any]], mutation: dict[str, Any]) -> list[dict[str, Any]]:
    result = [canonicalize(row) for row in productions]
    for row in result:
        if row["production_key"] != mutation["production_key"]:
            continue
        rhs = list(row["rhs"])
        index = mutation["symbol_index"]
        if mutation["op"] == "delete_terminal":
            del rhs[index]
        elif mutation["op"] == "replace_terminal":
            rhs[index] = {"terminal": mutation["value"]}
        else:
            rhs.insert(index, {"terminal": mutation["value"]})
        row["rhs"] = rhs
        return result
    raise InvalidInput("mutation productionが見つかりません")


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "syntax" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("Syntax-Based Testingのruntime metadataが不正です")
    input_label, start, productions, max_depth, mutations = _normalize(input_value)
    targets: list[dict[str, Any]] = []
    cases: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    covered = 0
    for production in productions:
        target_key = f"syntax:prod:{production['production_key']}"
        derivation = _derive(productions, start, max_depth, production["production_key"])
        if derivation is None:
            issues.append({"issue_type": "unreachable_production", "blocking": True, "target_key": target_key, "authority_refs": [], "route_to": "test-condition-design", "resume_skill": "test-condition-design"})
            targets.append({"target_key": target_key, "production_key": production["production_key"], "materializable": False, "execution": None, "authority_refs": []})
            continue
        covered += 1
        execution = {"input_label": input_label, "input_text": derivation["input_text"], "production_key_sequence": derivation["production_key_sequence"], "start": start}
        case = {"input_label": input_label, "input_text": derivation["input_text"], "production_key_sequence": derivation["production_key_sequence"], "production_key": production["production_key"], "materializable": True, "execution": execution}
        cases[(derivation["input_text"], tuple(derivation["production_key_sequence"]))] = case
        targets.append({"target_key": target_key, "production_key": production["production_key"], "input_label": input_label, "input_text": derivation["input_text"], "production_key_sequence": derivation["production_key_sequence"], "materializable": True, "execution": execution, "authority_refs": []})

    mutation_rows: list[dict[str, Any]] = []
    for mutation in mutations:
        target_key = f"syntax:mutation:{mutation['mutation_key']}"
        derivation = _derive(_mutated_productions(productions, mutation), start, max_depth, mutation["production_key"])
        if derivation is None:
            issues.append({"issue_type": "unreachable_mutation", "blocking": True, "target_key": target_key, "authority_refs": [], "route_to": "test-condition-design", "resume_skill": "test-condition-design"})
            mutation_rows.append({"target_key": target_key, "mutation": mutation, "invalid_candidate": True, "materializable": False, "execution": None})
            continue
        execution = {"input_label": input_label, "input_text": derivation["input_text"], "production_key_sequence": derivation["production_key_sequence"], "mutation": mutation, "invalid_candidate": True, "start": start}
        mutation_rows.append({"target_key": target_key, "mutation": mutation, "invalid_candidate": True, "input_label": input_label, "input_text": derivation["input_text"], "production_key_sequence": derivation["production_key_sequence"], "materializable": True, "execution": execution})
    targets = post_process_targets(metadata["model_key"], sorted(targets + mutation_rows, key=lambda row: row["target_key"]))
    valid_cases = sorted(cases.values(), key=lambda row: (row["input_text"], row["production_key_sequence"]))
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready" if not issues else "unresolved", "runtime_required": True, "deterministic_generated": True,
        "payload": {
            "input_label": input_label, "start": start, "productions": productions, "max_depth": max_depth, "mutations": mutations,
            "cases": valid_cases, "targets": targets,
            "coverage_summary": {"criterion": "production-coverage", "required": len(productions), "covered": covered, "complete": covered == len(productions) and not issues},
        },
        "issues": issues,
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
