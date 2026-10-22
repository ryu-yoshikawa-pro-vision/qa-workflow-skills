from __future__ import annotations

import importlib.util
import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from .common import AgentEvalError, canonical_fingerprint, sha256_bytes
from .workspace import FULL_SHA_RE, resolve_commit

SCENARIO_DIR = Path(__file__).resolve().parent / "scenarios" / "qa-training-store-checkout-payment-web-v1"
DEFAULT_TARGET_REVISION = "84ce165493649550832731a60cf436f8ae29c56b"
_OMIT_TOP_LEVEL = {".agents", ".codex"}
_OMIT_EXACT = {
    "AGENTS.md",
    "QA_AGENT.md",
    "docs/PROJECT_CONTEXT.md",
    "tests/repository-contract/skill-semantic-output-evals.test.ts",
    "tests/repository-contract/skill-trigger-evals.test.ts",
    "tests/repository-contract/skill-workflow-evals.test.ts",
    "tests/repository-contract/otel-skill-observer.test.ts",
    "tests/repository-contract/validate-skills.test.ts",
}
_OMIT_PREFIXES = (
    "docs/plans/",
    "docs/reports/",
    "training/agentic-qa/instructor/",
    "scripts/evals/",
)


def _git(root: Path, args: list[str], *, commit_identity: bool = False) -> str:
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    if commit_identity:
        env.update(
            {
                "GIT_AUTHOR_NAME": "Evaluator",
                "GIT_AUTHOR_EMAIL": "evaluator@invalid.local",
                "GIT_COMMITTER_NAME": "Evaluator",
                "GIT_COMMITTER_EMAIL": "evaluator@invalid.local",
            }
        )
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={root.resolve()}", "-C", str(root), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
        shell=False,
        env=env,
    )
    if completed.returncode != 0:
        raise AgentEvalError(f"sanitized target Git command failed: {args[0]}")
    return completed.stdout.strip()


def _is_excluded(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    return (
        bool(parts and parts[0] in _OMIT_TOP_LEVEL)
        or relative in _OMIT_EXACT
        or any(relative.startswith(prefix) for prefix in _OMIT_PREFIXES)
    )


def extract_revision_files(
    *,
    source_root: Path,
    revision: str,
    paths: list[str],
    max_total_bytes: int = 50_000_000,
) -> dict[str, bytes]:
    resolved = resolve_commit(source_root, revision)
    if not paths:
        return {}
    if any(PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts for path in paths):
        raise AgentEvalError("requested fixed-revision path is unsafe")
    archived = subprocess.run(
        ["git", "-c", f"safe.directory={source_root.resolve()}", "-C", str(source_root), "archive", "--format=tar", resolved, "--", *paths],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
        shell=False,
    )
    if archived.returncode != 0 or len(archived.stdout) > max_total_bytes:
        raise AgentEvalError("fixed-revision reference archive failed or exceeded its size limit")
    result: dict[str, bytes] = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            relative = PurePosixPath(member.name).as_posix()
            if member.isdir():
                continue
            if not member.isfile() or relative not in paths:
                raise AgentEvalError("fixed-revision reference archive contains an unsafe entry")
            stream = archive.extractfile(member)
            if stream is None:
                raise AgentEvalError("fixed-revision reference could not be read")
            content = stream.read()
            total += len(content)
            if total > max_total_bytes:
                raise AgentEvalError("fixed-revision references exceed their size limit")
            result[relative] = content
    missing = sorted(set(paths) - set(result))
    if missing:
        raise AgentEvalError(f"fixed-revision references are missing: {missing}")
    return result


def minimal_project_context() -> str:
    return """# Evaluation Project Context

Checkout / Payment Web workflow evaluation. This file supplies only the stable state root required by the existing qa-workflow contract.

<!-- qa-context-field:start key=qa.workflow_state_root type=path -->
/workspace/.qa-eval-output/workflow-state
<!-- qa-context-field:end -->
"""


def _validate_project_context(project_context: str) -> dict[str, Any]:
    parser_path = Path(__file__).resolve().parents[4] / "skills" / "qa-workflow" / "scripts" / "artifact_graph.py"
    spec = importlib.util.spec_from_file_location("qa_eval_fixed_artifact_graph", parser_path)
    if spec is None or spec.loader is None:
        raise AgentEvalError("fixed Project Context parser could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parsed = module.parse_project_context(project_context)
    required = module.validate_required_context_fields(
        parsed, ["qa.workflow_state_root"]
    )
    if required["status"] != "resolved":
        raise AgentEvalError("evaluation Project Context failed the existing stable-key parser")
    stable_value = parsed["fields"]["qa.workflow_state_root"]["value"]
    if os.name == "nt":
        # The production target runs in Linux Docker; Windows Path.is_absolute()
        # treats the container's POSIX path as relative, so validate its POSIX form here.
        if not PurePosixPath(stable_value).is_absolute():
            raise AgentEvalError("evaluation Project Context stable path is not POSIX-absolute")
        resolved = PurePosixPath(stable_value)
    else:
        resolved = module.workflow_state_root_from_project_context(project_context)
    if str(resolved) != "/workspace/.qa-eval-output/workflow-state":
        raise AgentEvalError("evaluation Project Context resolved an unexpected workflow root")
    return {"parsed": parsed, "required": required}


def _scan_workspace(root: Path) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            continue
        if relative == ".qa-eval-output" or relative.startswith(".qa-eval-output/"):
            continue
        if path.is_symlink():
            raise AgentEvalError(f"workspace contains a symlink: {relative}")
        if path.is_file():
            size = path.stat().st_size
            manifest[relative] = {"size": size, "sha256": _hash_file(path)}
    return manifest


def _hash_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def verify_workspace_unchanged(root: Path, baseline: dict[str, dict[str, Any]]) -> dict[str, Any]:
    current = _scan_workspace(root)
    changed = sorted(
        key for key in set(baseline) | set(current) if baseline.get(key) != current.get(key)
    )
    git_commits = _git(root, ["rev-list", "--count", "HEAD"])
    remotes = _git(root, ["remote"])
    return {
        "unchanged": not changed and git_commits == "1" and not remotes,
        "changed_paths": changed,
        "commit_count": int(git_commits),
        "remotes": remotes.splitlines() if remotes else [],
    }


def prepare_sanitized_target(
    *,
    source_root: Path,
    source_revision: str,
    candidate_skills_root: Path,
    verifier_capture_source: Path,
    destination: Path,
) -> dict[str, Any]:
    revision = resolve_commit(source_root, source_revision)
    if destination.exists():
        if not destination.is_dir() or any(destination.iterdir()):
            raise AgentEvalError("sanitized target destination must be an empty directory")
    else:
        destination.mkdir(parents=True)

    archived = subprocess.run(
        ["git", "-c", f"safe.directory={source_root.resolve()}", "-C", str(source_root), "archive", "--format=tar", revision],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
        shell=False,
    )
    if archived.returncode != 0:
        raise AgentEvalError("fixed target revision could not be archived")
    if len(archived.stdout) > 1024 * 1024 * 1024:
        raise AgentEvalError("target archive exceeds the configured safety limit")

    copied_files: list[dict[str, Any]] = []
    with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                raise AgentEvalError("target archive contains an unsafe path")
            normalized = relative.as_posix()
            if _is_excluded(normalized):
                continue
            if member.isdir():
                continue
            if not member.isfile():
                raise AgentEvalError("fixed target contains a non-regular tracked file")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = archive.extractfile(member)
            if stream is None:
                raise AgentEvalError("target tracked file could not be read")
            content = stream.read()
            target.write_bytes(content)
            copied_files.append(
                {"path": normalized, "size": len(content), "sha256": sha256_bytes(content)}
            )

    required_spec = destination / "docs/spec/features/checkout-and-payment.md"
    if not required_spec.is_file() or not (destination / "docs/spec/README.md").is_file():
        raise AgentEvalError("fixed target revision is missing required normative specifications")

    candidate_skills_root = candidate_skills_root.resolve()
    if not candidate_skills_root.is_dir():
        raise AgentEvalError("candidate Skill packages are missing")
    shutil.copytree(candidate_skills_root, destination / ".agents" / "skills")
    if not verifier_capture_source.is_file():
        raise AgentEvalError("verifier capture helper source is missing")
    capture_dir = destination / ".qa-eval-tools"
    capture_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(verifier_capture_source, capture_dir / "verifier_capture.py")

    project_context = minimal_project_context()
    context_result = _validate_project_context(project_context)
    (destination / "AGENTS.md").write_text(
        """# Evaluation Instructions

- 対象は固定revisionのCheckout / Payment Web分析・設計workflowです。
- Agent-visibleなSkillは `.agents/skills/` にEvaluatorが配置したSkill集合だけです。
- 規範仕様の優先順位は `docs/spec/README.md` に従ってください。
- Product Code、既存Product Test、規範仕様、配置Skill、評価用設定を変更しないでください。
- 成果物の書込みは `.qa-eval-output/` だけに行ってください。
- artifact-index.jsonには実ファイルの登録と各工程のrouting判断だけを記録してください。期待成果物本文や正解routingは与えません。
- runtime verifierを使う場合、対象Skillの`runtime_contract.py`へ渡すrequest bytesを`.qa-eval-output/.runtime-evidence/<skill>/<sha256-of-artifact-relative-path>/<unique-invocation-id>/request.json`へ保存し、`.qa-eval-tools/verifier_capture.py --skill <skill> --operation verify --request <request.json> --record <invocation-dir>`で実行してください。記録対象のSkillは`coverage-analysis`、`qa-workflow`、`spec-analysis`、`test-analysis`、`test-case-design`、`test-condition-design`、`test-requirement-design`、`usability-inspection`、`wcag-conformance-evaluation`です。requestを作っただけの自己申告JSONは実行証拠になりません。
- qa-workflowの`workflow_runtime.py`を使う場合も、実際の入力bytesを同じattempt内の`.runtime-evidence/qa-workflow/<sha256-of-artifact-relative-path>/<unique-invocation-id>/request.json`へ保存し、同じwrapperを`--skill qa-workflow --operation workflow-runtime`で実行してください。`valid`と`payload.can_complete`は別々に判定されます。
- commit、push、PR作成、評価資料の探索をしないでください。
""",
        encoding="utf-8",
    )
    context_path = destination / "docs/PROJECT_CONTEXT.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(project_context, encoding="utf-8")
    (destination / ".qa-eval-output").mkdir()

    baseline_manifest = _scan_workspace(destination)
    empty_hooks = destination.parent / f".{destination.name}-empty-hooks"
    empty_hooks.mkdir(exist_ok=True)
    try:
        subprocess.run(
            ["git", "init", "--quiet", str(destination)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=True,
            shell=False,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
        )
        _git(destination, ["config", "core.hooksPath", str(empty_hooks)])
        _git(destination, ["config", "commit.gpgsign", "false"])
        _git(destination, ["add", "--all"])
        _git(destination, ["commit", "--quiet", "-m", "Evaluator sanitized target baseline"], commit_identity=True)
        baseline_sha = _git(destination, ["rev-parse", "HEAD"])
        remotes = _git(destination, ["remote"])
        if remotes:
            raise AgentEvalError("sanitized target must not inherit a Git remote")
    finally:
        shutil.rmtree(empty_hooks, ignore_errors=False)

    copied_files.sort(key=lambda item: item["path"])
    return {
        "source_revision": revision,
        "synthetic_baseline_revision": baseline_sha,
        "source_manifest_fingerprint": canonical_fingerprint(copied_files),
        "baseline_manifest": baseline_manifest,
        "baseline_manifest_fingerprint": canonical_fingerprint(baseline_manifest),
        "copied_tracked_files": len(copied_files),
        "project_context_validation": context_result,
        "excluded_paths": sorted([*_OMIT_TOP_LEVEL, *_OMIT_EXACT, *_OMIT_PREFIXES]),
    }
