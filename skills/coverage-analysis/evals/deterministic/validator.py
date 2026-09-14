from __future__ import annotations

from collections import defaultdict
import re

from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS, clean, compute_graph_gaps, ids_in, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

E2E_HANDLING = {"新規E2E実装", "既存E2E再利用", "既存E2E拡張", "E2E対象外", "ブロック中"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("coverage-analysis", eval_id)
    tables = parse_tables(text)
    authority_table = find_table(tables, section_contains="仕様根拠 / プロダクトリスクの閉鎖状況", required_headers=("上流ID", "状態"))
    item_table = find_table(tables, section_contains="カバレッジ項目の扱い", required_headers=("カバレッジ項目ID / 項目", "扱い"))
    matrix_table = find_table(tables, section_contains="カバレッジマトリクス", required_headers=("上流ID / 挙動", "カバレッジ", "修正Skill / 層"))
    orphan_table = find_table(tables, section_contains="陳腐化 / 孤立分析", required_headers=("成果物ID", "分類", "修正Skill / 層"))

    # カバレッジ分析は部分実行を許容するため、個別ビューは分析対象に応じて省略できる。
    # 正規の最低必須出力はカバレッジマトリクスとする。
    result.add(
        "COV-D007",
        matrix_table is not None,
        "カバレッジマトリクスが存在すること",
        evidence="カバレッジマトリクス" if matrix_table is None else None,
    )

    authority_rows = nonempty_rows(authority_table)
    item_rows = nonempty_rows(item_table)
    matrix_rows = nonempty_rows(matrix_table)
    orphan_rows = nonempty_rows(orphan_table)

    graph = expected.get("graph", {})
    known = set(graph.get("node_types", {}))
    output_refs = []
    for row in authority_rows + item_rows + matrix_rows + orphan_rows:
        output_refs.extend(ids_in(" ".join(row.values())))
    if "graph" in expected:
        unknown = sorted({r for r in output_refs if r not in known})
    else:
        unknown = []
    result.add("COV-D001", not unknown, "カバレッジ出力の参照がフィクスチャグラフに存在すること", evidence=unknown or None)

    gaps = compute_graph_gaps(graph)
    recognized, blocked = set(), []
    searchable = authority_rows + item_rows + matrix_rows + orphan_rows
    for gap in gaps:
        for row in searchable:
            if gap not in ids_in(" ".join(row.values())):
                continue
            status = " ".join([row.get("状態", ""), row.get("カバレッジ", ""), row.get("扱い", ""), row.get("根拠 / ギャップ", "")])
            if any(t in status for t in ("未閉鎖", "未網羅", "未充足", "部分", "ギャップ", "Gap")):
                recognized.add(gap)
            if "ブロック中" in status:
                blocked.append(gap)
    result.add("COV-D002", gaps.issubset(recognized), "計算されたグラフギャップがカバレッジ分析で認識されていること", evidence={"computed": sorted(gaps), "recognized": sorted(recognized)} if not gaps.issubset(recognized) else None)
    result.add("COV-D003", not blocked, "フィクスチャ上の根拠なしに下流成果物の欠落をブロック中へ分類しないこと", evidence=sorted(set(blocked)) or None)

    node_types = graph.get("node_types", {})
    edges = graph.get("edges", [])
    incoming = defaultdict(set)
    for src, dst in edges:
        incoming[dst].add(src)
    orphan = [n for n, t in node_types.items() if t in {"TR", "TCN", "CI", "TC"} and not incoming.get(n)]
    reported = {ref for row in orphan_rows if "孤立" in clean(row.get("分類", "")) for ref in ids_in(row.get("成果物ID", ""))}
    result.add("COV-D004", set(orphan).issubset(reported) if orphan else True, "フィクスチャグラフの孤立ノードが存在する場合に報告されていること", evidence={"computed": orphan, "reported": sorted(reported)} if orphan and not set(orphan).issubset(reported) else None)

    expected_fix = expected.get("expected_fix_skills", {})
    mismatches = []
    for target, skill in expected_fix.items():
        matching = [r for r in matrix_rows + orphan_rows if target in ids_in(" ".join(r.values()))]
        if not matching:
            mismatches.append({"target": target, "expected": skill, "reason": "target missing from repair analysis"})
        elif not any(skill in r.get("修正Skill / 層", "") for r in matching):
            mismatches.append({"target": target, "expected": skill, "reason": "repair skill mismatch"})
    result.add("COV-D005", not mismatches, "既知の修正ルーティング対象が存在し、正規の責任Skillを使用すること", evidence=mismatches or None)

    invalid = sorted({
        clean(r.get("修正Skill / 層", "")).split()[0]
        for r in matrix_rows + orphan_rows
        if clean(r.get("修正Skill / 層", "")) and clean(r.get("修正Skill / 層", "")).split()[0] not in CANONICAL_SKILLS
    })
    result.add("COV-D006", not invalid, "Skill名だけを指定する修正先は正規Skill名であること", evidence=invalid or None)

    tc_e2e_table = find_table(
        tables,
        section_contains="TC → E2E実装対応表",
        required_headers=("TC ID", "扱い", "E2E実装参照"),
    )
    expected_tc_e2e = expected.get("expected_tc_e2e", [])
    if expected_tc_e2e:
        result.add(
            "COV-D008",
            tc_e2e_table is not None,
            "TC → E2E実装の対象別対応表が存在すること",
            evidence="TC → E2E実装対応表" if tc_e2e_table is None else None,
        )
    tc_e2e_rows = nonempty_rows(tc_e2e_table)
    tc_e2e_mismatches = []
    for item in expected_tc_e2e:
        tc_id = clean(str(item.get("tc_id", "")))
        match = next((row for row in tc_e2e_rows if clean(row.get("TC ID", "")) == tc_id), None)
        if match is None:
            tc_e2e_mismatches.append({"tc_id": tc_id, "reason": "missing"})
            continue
        actual_handling = clean(match.get("扱い", ""))
        actual_ref = clean(match.get("E2E実装参照", ""))
        expected_handling = clean(str(item.get("handling", "")))
        if actual_handling not in E2E_HANDLING or actual_handling != expected_handling:
            tc_e2e_mismatches.append({"tc_id": tc_id, "expected_handling": expected_handling, "actual_handling": actual_handling})
        if expected_handling in {"新規E2E実装", "既存E2E再利用", "既存E2E拡張"} and not actual_ref:
            tc_e2e_mismatches.append({"tc_id": tc_id, "reason": "implementation reference missing"})
        if "implementation_ref" in item and actual_ref != clean(str(item["implementation_ref"])):
            tc_e2e_mismatches.append({"tc_id": tc_id, "expected_ref": item["implementation_ref"], "actual_ref": actual_ref})
    if expected_tc_e2e:
        result.add("COV-D009", not tc_e2e_mismatches, "TCごとのE2E扱いと実装参照がフィクスチャと一致すること", evidence=tc_e2e_mismatches or None)

    expected_e2e_execution = expected.get("expected_e2e_execution", [])
    if expected_e2e_execution:
        result.add(
            "COV-D010",
            matrix_table is not None,
            "既存カバレッジマトリクスでE2E実装 → 実行結果を追跡できること",
            evidence="カバレッジマトリクス" if matrix_table is None else None,
        )
    e2e_result_rows = matrix_rows
    execution_mismatches = []
    for item in expected_e2e_execution:
        ref = clean(str(item.get("implementation_ref", "")))
        match = next((row for row in e2e_result_rows if ref and clean(row.get("上流ID / 挙動", "")) == ref), None)
        if match is None:
            execution_mismatches.append({"implementation_ref": ref, "reason": "missing"})
            continue
        result_ref = clean(match.get("下流ID / 扱い", ""))
        result_context = " ".join(
            clean(match.get(field, ""))
            for field in ("根拠 / ギャップ", "推奨対応")
            if clean(match.get(field, ""))
        )
        outcome = " ".join(
            clean(match.get(field, ""))
            for field in ("カバレッジ", "根拠 / ギャップ", "推奨対応")
            if clean(match.get(field, ""))
        )
        if not result_ref:
            execution_mismatches.append({"implementation_ref": ref, "reason": "result reference missing"})
        if not outcome:
            execution_mismatches.append({"implementation_ref": ref, "reason": "result or unexecuted reason missing"})
        if "result_ref" in item and clean(str(item["result_ref"])) != result_ref:
            execution_mismatches.append({"implementation_ref": ref, "reason": "expected result reference missing", "expected": item["result_ref"]})
        if "result_contains" in item and str(item["result_contains"]) not in result_ref + " " + result_context + " " + outcome:
            execution_mismatches.append({"implementation_ref": ref, "reason": "expected result text missing"})
    if expected_e2e_execution:
        result.add("COV-D011", not execution_mismatches, "E2E実装参照からresolved primary TestCase / 実行結果と結果または未実行理由へ追跡できること", evidence=execution_mismatches or None)

    if expected.get("tc_absent"):
        fabricated = sorted(set(re.findall(r"\bTC-\d{3}\b", text)))
        result.add("COV-D012", not fabricated, "TCなし経路でTC IDを創作しないこと", evidence=fabricated or None)
    return result
