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
    result = EvalResult("context-signal-audit", eval_id)
    try:
        content = _payload(text)
        artifact = parse_canonical_json(content)
        kind = expected.get("kind")
        validate_artifact(artifact, kind)
    except (ContractError, TypeError, ValueError) as exc:
        result.add(
            "CSA-OUT-001",
            False,
            "正規batch契約を満たすcanonical JSON",
            evidence=str(exc),
        )
        return result
    result.add(
        "CSA-OUT-001",
        kind == "context-signal-batch",
        "成果物kindがcontext-signal-batchであること",
    )
    result.add(
        "CSA-OUT-002",
        artifact.get("artifact_ref")
        == f"context-signal-batch/{artifact.get('batch_identity')}.json",
        "kind直下のroot相対batch refであること",
    )
    result.add(
        "CSA-OUT-003",
        artifact.get("scan_completeness") in {"complete", "partial"},
        "失敗状態を正常batchとして保存しないこと",
    )
    return result
