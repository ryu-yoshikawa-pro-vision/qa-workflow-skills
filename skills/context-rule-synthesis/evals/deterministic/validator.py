from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

from context_artifacts import (  # noqa: E402
    ContractError,
    parse_canonical_json,
    validate_artifact,
)

from scripts.skills.evals.deterministic.result import EvalResult  # noqa: E402


def _payload(text: str) -> str:
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL)
    return blocks[0] if len(blocks) == 1 else text.strip()


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("context-rule-synthesis", eval_id)
    try:
        content = _payload(text)
        artifact = parse_canonical_json(content)
        kind = expected.get("kind")
        validate_artifact(artifact, kind)
    except (ContractError, TypeError, ValueError) as exc:
        result.add(
            "CRS-OUT-001",
            False,
            "正規candidateまたはrun契約を満たすcanonical JSON",
            evidence=str(exc),
        )
        return result
    result.add(
        "CRS-OUT-001",
        kind in {"context-rule-candidate", "context-synthesis-run"},
        "成果物kindがcandidateまたはsynthesis runであること",
    )
    result.add(
        "CRS-OUT-002",
        isinstance(artifact.get("artifact_ref"), str)
        and artifact["artifact_ref"]
        == f"{kind}/{artifact.get('candidate_identity', artifact.get('run_identity'))}.json",
        "kind直下のroot相対artifact refであること",
    )
    if kind == "context-synthesis-run":
        status = artifact.get("result_summary", {}).get("status")
        result.add(
            "CRS-OUT-003",
            status
            in {
                "in_progress",
                "completed",
                "completed_zero_changes",
                "blocked_incomplete",
            },
            "run状態を正規の完了状態と区別すること",
        )
    return result
