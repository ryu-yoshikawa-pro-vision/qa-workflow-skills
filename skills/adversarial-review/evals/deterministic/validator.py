from __future__ import annotations

from collections import Counter

from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS, ID_PATTERNS, add_allowed_assertion, add_duplicate_assertion, add_required_fields_assertion, clean, ids_in, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

SEVERITIES = {"致命的", "重大", "軽微", "提案"}
TREATMENTS = {"未処置", "修正済み", "残存リスクとして受容", "ブロック中"}
REPAIR_TARGETS = CANONICAL_SKILLS | {"案件コンテキスト / 仕様決定"}


def _normalize_treatment(value: str) -> str:
    value = clean(value)
    return "残存リスクとして受容" if value.startswith("残存リスクとして受容") else value


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("adversarial-review", eval_id)
    tables = parse_tables(text)
    summary_table = find_table(tables, section_contains="指摘概要", required_headers=("重要度", "件数"))
    findings_table = find_table(tables, section_contains="指摘一覧", required_headers=("指摘ID", "重要度", "処置"))
    missing_tables = [label for label, table in (("指摘概要", summary_table), ("指摘一覧", findings_table)) if table is None]
    result.add("REV-D011", not missing_tables, "反証レビューの正規テーブルが存在すること", evidence=missing_tables or None)

    summary = nonempty_rows(summary_table)
    findings = nonempty_rows(findings_table)
    add_required_fields_assertion(result, "REV-D012", findings, ("指摘ID", "重要度", "対象成果物 / 位置", "問題", "根拠", "影響", "推奨修正", "修正Skill / 層", "処置"), "指摘ID", "レビュー指摘")
    add_allowed_assertion(result, "REV-D013", (r.get("重要度", "") for r in summary), SEVERITIES, "概要の重要度")
    add_duplicate_assertion(result, "REV-D014", [clean(r.get("重要度", "")) for r in summary], "概要の重要度")

    ids = [clean(r.get("指摘ID", "")) for r in findings]
    bad = [v for v in ids if not ID_PATTERNS["REV"].fullmatch(v)]
    result.add("REV-D001", not bad, "指摘IDがREV-xxx形式であること", evidence=bad or None)
    add_duplicate_assertion(result, "REV-D002", ids, "指摘ID")
    add_allowed_assertion(result, "REV-D003", (r.get("重要度", "") for r in findings), SEVERITIES, "重要度")

    invalid = sorted({_normalize_treatment(r.get("処置", "")) for r in findings if _normalize_treatment(r.get("処置", "")) not in TREATMENTS})
    result.add("REV-D004", not invalid, "処置が許可値であること", evidence=invalid or None)

    unknown = []
    if "known_artifact_ids" in expected:
        known = set(expected["known_artifact_ids"])
        for row in findings:
            refs = ids_in(row.get("対象成果物 / 位置", ""))
            if not refs or any(ref not in known for ref in refs):
                unknown.append({"finding": row.get("指摘ID"), "targets": refs})
    result.add("REV-D005", not unknown, "指摘対象の成果物が存在すること", evidence=unknown or None)

    bad_targets = sorted({clean(r.get("修正Skill / 層", "")) for r in findings if clean(r.get("修正Skill / 層", "")) and clean(r.get("修正Skill / 層", "")) not in REPAIR_TARGETS})
    result.add("REV-D006", not bad_targets, "修正先が反証レビュー契約で許可されていること", evidence=bad_targets or None)

    fatal = [clean(r.get("指摘ID", "")) for r in findings if clean(r.get("重要度", "")) == "致命的" and _normalize_treatment(r.get("処置", "")) == "残存リスクとして受容"]
    result.add("REV-D007", not fatal, "致命的な指摘を残存リスクとして受容しないこと", evidence=fatal or None)

    major = []
    approvals_specified = "approved_risk_acceptances" in expected
    approved = expected.get("approved_risk_acceptances", {})
    for row in findings:
        if clean(row.get("重要度", "")) != "重大" or _normalize_treatment(row.get("処置", "")) != "残存リスクとして受容":
            continue
        rid = clean(row.get("指摘ID", ""))
        approval_cell = clean(row.get("処置根拠 / 承認参照", ""))
        if approvals_specified:
            required_approval = approved.get(rid)
            if not required_approval or required_approval not in approval_cell:
                major.append({"id": rid, "expected_approval": required_approval, "actual": approval_cell})
        elif not approval_cell:
            major.append({"id": rid, "expected_approval": None, "actual": approval_cell})
    result.add("REV-D008", not major, "重大な残存リスク受容には、フィクスチャ指定時は承認参照、それ以外では理由 / 承認参照が必要であること", evidence=major or None)

    actual = Counter(clean(r.get("重要度", "")) for r in findings)
    summary_counts, bad_count = {}, []
    for row in summary:
        sev = clean(row.get("重要度", ""))
        try:
            summary_counts[sev] = int(clean(row.get("件数", "")))
        except ValueError:
            bad_count.append({"severity": sev, "count": row.get("件数")})
    mismatch = {s: {"summary": summary_counts.get(s), "actual": actual.get(s, 0)} for s in SEVERITIES if summary_counts.get(s) != actual.get(s, 0)}
    result.add("REV-D009", not bad_count and not mismatch, "重要度別の概要件数が指摘行と一致すること", evidence={"invalid_counts": bad_count, "mismatches": mismatch} if bad_count or mismatch else None)

    missed = []
    for defect in expected.get("expected_defects", []):
        target = defect["target_id"]
        contains = defect.get("contains")
        severity = defect.get("severity")
        repair_target = defect.get("repair_target")
        matched = any(
            target in ids_in(row.get("対象成果物 / 位置", ""))
            and (not contains or contains in row.get("問題", "") or contains in row.get("根拠", ""))
            and (severity is None or clean(row.get("重要度", "")) == severity)
            and (repair_target is None or clean(row.get("修正Skill / 層", "")) == repair_target)
            for row in findings
        )
        if not matched:
            missed.append(defect)
    result.add("REV-D010", not missed, "フィクスチャで指定した決定論的欠陥と属性が一致すること", evidence=missed or None)
    return result
