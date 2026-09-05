from __future__ import annotations

from collections import Counter

from ..common import CANONICAL_SKILLS, ID_PATTERNS, add_allowed_assertion, add_duplicate_assertion, add_required_fields_assertion, clean, ids_in, nonempty_rows
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

SEVERITIES = {"致命的", "重大", "軽微", "提案"}
TREATMENTS = {"未処置", "修正済み", "残存リスクとして受容", "Blocked"}
REPAIR_TARGETS = CANONICAL_SKILLS | {"Project Context / 仕様決定"}


def _normalize_treatment(value: str) -> str:
    value = clean(value)
    return "残存リスクとして受容" if value.startswith("残存リスクとして受容") else value


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("adversarial-review", eval_id)
    tables = parse_tables(text)
    summary_table = find_table(tables, section_contains="指摘概要", required_headers=("重要度", "件数"))
    findings_table = find_table(tables, section_contains="指摘一覧", required_headers=("指摘ID", "重要度", "処置"))
    missing_tables = [label for label, table in (("指摘概要", summary_table), ("指摘一覧", findings_table)) if table is None]
    result.add("REV-D011", not missing_tables, "Canonical adversarial-review tables must exist", evidence=missing_tables or None)

    summary = nonempty_rows(summary_table)
    findings = nonempty_rows(findings_table)
    add_required_fields_assertion(result, "REV-D012", findings, ("指摘ID", "重要度", "対象成果物 / 位置", "問題", "根拠", "影響", "推奨修正", "修正Skill / 層", "処置"), "指摘ID", "Review finding")
    add_allowed_assertion(result, "REV-D013", (r.get("重要度", "") for r in summary), SEVERITIES, "Summary severity")
    add_duplicate_assertion(result, "REV-D014", [clean(r.get("重要度", "")) for r in summary], "Summary severity")

    ids = [clean(r.get("指摘ID", "")) for r in findings]
    bad = [v for v in ids if not ID_PATTERNS["REV"].fullmatch(v)]
    result.add("REV-D001", not bad, "Review finding IDs must use REV-xxx", evidence=bad or None)
    add_duplicate_assertion(result, "REV-D002", ids, "Review finding IDs")
    add_allowed_assertion(result, "REV-D003", (r.get("重要度", "") for r in findings), SEVERITIES, "Severity")

    invalid = sorted({_normalize_treatment(r.get("処置", "")) for r in findings if _normalize_treatment(r.get("処置", "")) not in TREATMENTS})
    result.add("REV-D004", not invalid, "Treatment must use allowed values", evidence=invalid or None)

    unknown = []
    if "known_artifact_ids" in expected:
        known = set(expected["known_artifact_ids"])
        for row in findings:
            refs = ids_in(row.get("対象成果物 / 位置", ""))
            if not refs or any(ref not in known for ref in refs):
                unknown.append({"finding": row.get("指摘ID"), "targets": refs})
    result.add("REV-D005", not unknown, "Finding target artifacts must exist", evidence=unknown or None)

    bad_targets = sorted({clean(r.get("修正Skill / 層", "")) for r in findings if clean(r.get("修正Skill / 層", "")) and clean(r.get("修正Skill / 層", "")) not in REPAIR_TARGETS})
    result.add("REV-D006", not bad_targets, "Repair target must be allowed by the adversarial-review contract", evidence=bad_targets or None)

    fatal = [clean(r.get("指摘ID", "")) for r in findings if clean(r.get("重要度", "")) == "致命的" and _normalize_treatment(r.get("処置", "")) == "残存リスクとして受容"]
    result.add("REV-D007", not fatal, "Fatal findings cannot be accepted as residual risk", evidence=fatal or None)

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
    result.add("REV-D008", not major, "Major residual-risk acceptance requires fixture approval when supplied, otherwise rationale/approval reference", evidence=major or None)

    actual = Counter(clean(r.get("重要度", "")) for r in findings)
    summary_counts, bad_count = {}, []
    for row in summary:
        sev = clean(row.get("重要度", ""))
        try:
            summary_counts[sev] = int(clean(row.get("件数", "")))
        except ValueError:
            bad_count.append({"severity": sev, "count": row.get("件数")})
    mismatch = {s: {"summary": summary_counts.get(s), "actual": actual.get(s, 0)} for s in SEVERITIES if summary_counts.get(s) != actual.get(s, 0)}
    result.add("REV-D009", not bad_count and not mismatch, "Severity summary counts must match finding rows", evidence={"invalid_counts": bad_count, "mismatches": mismatch} if bad_count or mismatch else None)

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
    result.add("REV-D010", not missed, "Fixture-backed deterministic defects and specified attributes must match", evidence=missed or None)
    return result
