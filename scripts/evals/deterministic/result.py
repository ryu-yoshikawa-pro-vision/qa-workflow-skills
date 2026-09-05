from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class AssertionResult:
    id: str
    status: str  # pass | fail | warning
    severity: str  # error | warning
    message: str
    evidence: Any = None


class EvalResult:
    def __init__(self, skill: str, eval_id: str) -> None:
        self.skill = skill
        self.eval_id = eval_id
        self.assertions: list[AssertionResult] = []

    def add(
        self,
        assertion_id: str,
        ok: bool,
        message: str,
        *,
        severity: str = "error",
        evidence: Any = None,
    ) -> None:
        if severity not in {"error", "warning"}:
            raise ValueError(f"unsupported severity: {severity}")
        if ok:
            status = "pass"
        elif severity == "warning":
            status = "warning"
        else:
            status = "fail"
        self.assertions.append(
            AssertionResult(
                id=assertion_id,
                status=status,
                severity=severity,
                message=message,
                evidence=evidence,
            )
        )

    def extend(self, assertions: Iterable[AssertionResult]) -> None:
        self.assertions.extend(assertions)

    @property
    def status(self) -> str:
        return "fail" if any(a.status == "fail" for a in self.assertions) else "pass"

    def to_dict(self) -> dict[str, Any]:
        errors = sum(a.status == "fail" for a in self.assertions)
        warnings = sum(a.status == "warning" for a in self.assertions)
        passed = sum(a.status == "pass" for a in self.assertions)
        total = len(self.assertions)
        return {
            "skill": self.skill,
            "eval_id": self.eval_id,
            "status": self.status,
            "summary": {
                "errors": errors,
                "warnings": warnings,
                "passed": passed,
                "total": total,
                "assertion_pass_rate": (passed / total) if total else 1.0,
            },
            "assertions": [asdict(a) for a in self.assertions],
        }
