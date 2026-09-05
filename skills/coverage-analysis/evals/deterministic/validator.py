from __future__ import annotations

from collections import defaultdict

from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS, clean, compute_graph_gaps, ids_in, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("coverage-analysis", eval_id)
    tables = parse_tables(text)
    authority_table = find_table(tables, section_contains="Authority / Product Riskの閉鎖状況", required_headers=("上流ID", "状態"))
    item_table = find_table(tables, section_contains="Coverage ItemのDisposition", required_headers=("Coverage Item ID / 項目", "Disposition"))
    matrix_table = find_table(tables, section_contains="カバレッジマトリクス", required_headers=("上流ID / 挙動", "カバレッジ", "修正Skill / 層"))
    orphan_table = find_table(tables, section_contains="陳腐化 / 孤立分析", required_headers=("成果物ID", "分類", "修正Skill / 層"))

    # Coverage AnalysisはPartial実行を許容するため、個別ビューは分析対象に応じて省略できる。
    # Canonicalな最低必須Outputはカバレッジマトリクスとする。
    result.add(
        "COV-D007",
        matrix_table is not None,
        "Coverage matrix must exist",
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
    result.add("COV-D001", not unknown, "Coverage output references must exist in fixture graph", evidence=unknown or None)

    gaps = compute_graph_gaps(graph)
    recognized, blocked = set(), []
    searchable = authority_rows + item_rows + matrix_rows + orphan_rows
    for gap in gaps:
        for row in searchable:
            if gap not in ids_in(" ".join(row.values())):
                continue
            status = " ".join([row.get("状態", ""), row.get("カバレッジ", ""), row.get("Disposition", ""), row.get("根拠 / ギャップ", "")])
            if any(t in status for t in ("未閉鎖", "未網羅", "未充足", "部分", "ギャップ", "Gap")):
                recognized.add(gap)
            if "Blocked" in status:
                blocked.append(gap)
    result.add("COV-D002", gaps.issubset(recognized), "Computed graph gaps must be recognized by coverage-analysis", evidence={"computed": sorted(gaps), "recognized": sorted(recognized)} if not gaps.issubset(recognized) else None)
    result.add("COV-D003", not blocked, "Missing downstream artifacts must not be classified as Blocked without fixture basis", evidence=sorted(set(blocked)) or None)

    node_types = graph.get("node_types", {})
    edges = graph.get("edges", [])
    incoming = defaultdict(set)
    for src, dst in edges:
        incoming[dst].add(src)
    orphan = [n for n, t in node_types.items() if t in {"TR", "TCN", "CI", "TC"} and not incoming.get(n)]
    reported = {ref for row in orphan_rows if "孤立" in clean(row.get("分類", "")) for ref in ids_in(row.get("成果物ID", ""))}
    result.add("COV-D004", set(orphan).issubset(reported) if orphan else True, "Fixture graph orphan nodes must be reported when present", evidence={"computed": orphan, "reported": sorted(reported)} if orphan and not set(orphan).issubset(reported) else None)

    expected_fix = expected.get("expected_fix_skills", {})
    mismatches = []
    for target, skill in expected_fix.items():
        matching = [r for r in matrix_rows + orphan_rows if target in ids_in(" ".join(r.values()))]
        if not matching:
            mismatches.append({"target": target, "expected": skill, "reason": "target missing from repair analysis"})
        elif not any(skill in r.get("修正Skill / 層", "") for r in matching):
            mismatches.append({"target": target, "expected": skill, "reason": "repair skill mismatch"})
    result.add("COV-D005", not mismatches, "Known repair routing target must exist and use canonical responsible Skill", evidence=mismatches or None)

    invalid = sorted({
        clean(r.get("修正Skill / 層", "")).split()[0]
        for r in matrix_rows + orphan_rows
        if clean(r.get("修正Skill / 層", "")) and clean(r.get("修正Skill / 層", "")).split()[0] not in CANONICAL_SKILLS
    })
    result.add("COV-D006", not invalid, "Repair Skill must be canonical when a bare Skill name is supplied", evidence=invalid or None)
    return result
