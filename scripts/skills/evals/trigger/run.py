"""Real-agent trigger evaluation runner (Claude Code headless).

Every Skill of the repository is made available at the same time in an isolated
workspace (``.claude/skills/<name>``). Each query runs in its own headless
Claude Code process with a clean environment and configuration directory, and the
Skill that the model actually loads is observed from the ``Skill`` tool call in
the stream-json log, never inferred from the answer text.

Run rules (EVALS.md): ``trigger_rate = triggers / valid attempts``; a positive
query passes at ``> 0.5``, a negative query at ``< 0.5``. A timed-out, killed or
otherwise unobserved attempt is *invalid*: it is kept in the log and excluded
from the rate, never counted as "not triggered".

Examples::

    python scripts/skills/evals/trigger/run.py --skills defect-management \\
        --queries-per-class 2 --repeat 3 --estimate
    python scripts/skills/evals/trigger/run.py --skills defect-management \\
        --queries-per-class 2 --repeat 3 --out results.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"
DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_MAX_TURNS = 6
OBSERVED_SECONDS_PER_RUN = 15  # measured: mean 14.8 s per run (2026-11-13, early stop)
PARENT_SESSION_ENV = (
    "CLAUDECODE",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_PID",
    "CLAUDE_EFFORT",
    "CLAUDE_CODE_MESSAGING_SOCKET",
    "CLAUDE_CODE_SESSION_ATTENDED",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_EXECPATH",
    "CLAUDE_CODE_MESSAGING_TOKEN",
)


def repository_skills(skills_root: Path = SKILLS_ROOT) -> list[str]:
    return sorted(p.parent.name for p in skills_root.glob("*/SKILL.md"))


def select_queries(
    skills: list[str],
    per_class: int,
    *,
    skills_root: Path = SKILLS_ROOT,
    dataset: str = "validation_queries.json",
) -> list[dict[str, Any]]:
    """First ``per_class`` positive and negative queries of each Skill, in file order."""
    selected = []
    for skill in skills:
        rows = json.loads(
            (skills_root / skill / "evals" / "trigger" / dataset).read_text(
                encoding="utf-8"
            )
        )
        for flag in (True, False):
            picked = [r for r in rows if r["should_trigger"] is flag][:per_class]
            for index, row in enumerate(picked):
                selected.append(
                    {
                        "skill": skill,
                        "should_trigger": flag,
                        "query": row["query"],
                        "query_id": f"{skill}:{dataset.split('_')[0]}:{'pos' if flag else 'neg'}:{index}",
                    }
                )
    return selected


def build_workspace(workdir: Path, skills_root: Path = SKILLS_ROOT) -> list[str]:
    """Make every repository Skill available (SKILL.md and supporting files only)."""
    target = workdir / ".claude" / "skills"
    if target.exists():
        shutil.rmtree(target)
    names = repository_skills(skills_root)
    for name in names:
        shutil.copytree(
            skills_root / name,
            target / name,
            ignore=shutil.ignore_patterns("evals", "tests", "__pycache__"),
        )
    return names


def clean_environment(config_dir: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in PARENT_SESSION_ENV}
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return env


def make_config_dir(base: Path, credentials: Path) -> Path:
    """Isolated config: credentials only, so no memory, settings or user skills load.

    The credentials file is linked (not copied) so a refreshed token is written
    back to the original instead of rotating it away.
    """
    config = base / "config"
    config.mkdir(parents=True, exist_ok=True)
    link = config / ".credentials.json"
    if not link.exists():
        link.symlink_to(credentials)
    return config


SKILL_MD_MARKER = "/.claude/skills/"


def _tool_uses(line: str) -> list[dict[str, Any]]:
    try:
        event = json.loads(line)
    except ValueError:
        return []
    if not isinstance(event, dict) or event.get("type") != "assistant":
        return []
    content = (event.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]


def skill_loads_in_line(line: str) -> list[tuple[str, str]]:
    """``(skill, method)`` for each Skill load in one stream-json line.

    ``method`` is ``skill_tool`` (the ``Skill`` tool) or ``read_skill_md`` (the
    model read ``.claude/skills/<name>/SKILL.md`` directly, which loads the same
    instructions). Reading any other file of a Skill, or mentioning a Skill in
    text, is not a load.
    """
    loads: list[tuple[str, str]] = []
    for block in _tool_uses(line):
        tool_input = block.get("input")
        if not isinstance(tool_input, dict):
            continue
        if block.get("name") == "Skill" and isinstance(tool_input.get("skill"), str):
            loads.append((tool_input["skill"], "skill_tool"))
        elif block.get("name") == "Read" and isinstance(
            tool_input.get("file_path"), str
        ):
            path = tool_input["file_path"].replace("\\", "/")
            head, marker, tail = path.rpartition(SKILL_MD_MARKER)
            parts = tail.split("/")
            if marker and len(parts) == 2 and parts[1] == "SKILL.md" and parts[0]:
                loads.append((parts[0], "read_skill_md"))
    return loads


def skill_loads(stream: str) -> list[tuple[str, str]]:
    return [load for line in stream.splitlines() for load in skill_loads_in_line(line)]


def invoked_skills(stream: str) -> list[str]:
    """Skills loaded (by either method) in a stream-json log, in order."""
    return [name for name, _ in skill_loads(stream)]


def skill_call_in_line(line: str) -> str | None:
    """The first Skill loaded in one stream-json line, if any."""
    loads = skill_loads_in_line(line)
    return loads[0][0] if loads else None


def observed_result(stream: str) -> dict[str, Any] | None:
    for line in reversed(stream.splitlines()):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            return event
    return None


def classify_attempt(stream: str, *, timed_out: bool, returncode: int | None) -> str:
    """``valid`` only when a result event was observed for a finished process."""
    if timed_out:
        return "invalid_timeout"
    result = observed_result(stream)
    init_seen = '"subtype":"init"' in stream.replace(" ", "")
    if result is None or not init_seen:
        return "invalid_no_result"
    if result.get("is_error") and result.get("subtype") not in {
        "error_max_turns",
        "success",
    }:
        return "invalid_error"
    return "valid"


def run_attempt(
    entry: dict[str, Any],
    attempt: int,
    *,
    workdir: Path,
    config_dir: Path,
    model: str,
    timeout: int,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> dict[str, Any]:
    """Run one query. The decision is observed at the first ``Skill`` tool call.

    The process is stopped as soon as a Skill is loaded (the decision is made).
    Without a Skill call it runs until the turn limit, so a model that first
    explores the workspace is not cut off before it chooses. A run that does not
    finish within ``timeout`` is invalid and never counted as "not triggered".
    """
    command = [
        "claude",
        "-p",
        entry["query"],
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        "Skill",
        "--max-turns",
        str(max_turns),
    ]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=workdir,
        env=clean_environment(config_dir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
    )
    timed_out = threading.Event()

    def kill() -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def on_timeout() -> None:
        timed_out.set()
        kill()

    timer = threading.Timer(timeout, on_timeout)
    timer.start()
    lines: list[str] = []
    early_skill: str | None = None
    try:
        assert process.stdout is not None
        for line in process.stdout:
            lines.append(line)
            early_skill = skill_call_in_line(line)
            if early_skill is not None:
                kill()
                break
    finally:
        timer.cancel()
        process.wait()
    stream = "".join(lines)
    if timed_out.is_set():
        status = "invalid_timeout"
    elif early_skill is not None:
        status = (
            "valid"
            if '"subtype":"init"' in stream.replace(" ", "")
            else ("invalid_no_result")
        )
    else:
        status = classify_attempt(
            stream, timed_out=False, returncode=process.returncode
        )
    loaded = invoked_skills(stream) if status == "valid" else []
    return {
        "query_id": entry["query_id"],
        "skill": entry["skill"],
        "should_trigger": entry["should_trigger"],
        "attempt": attempt,
        "status": status,
        "invoked_skills": loaded,
        "load_methods": [m for _, m in skill_loads(stream)][:1]
        if status == "valid"
        else [],
        "target_triggered": entry["skill"] in loaded,
        "stopped_at_first_skill_call": early_skill is not None,
        "seconds": round(time.monotonic() - started, 1),
        "stream_tail": stream[-300:] if status != "valid" else "",
    }


def aggregate(
    attempts: list[dict[str, Any]], *, minimum_valid: int = 2
) -> list[dict[str, Any]]:
    """Per-query rates over valid attempts, with the repository thresholds."""
    by_query: dict[str, list[dict[str, Any]]] = {}
    for row in attempts:
        by_query.setdefault(row["query_id"], []).append(row)
    summary = []
    for query_id, rows in sorted(by_query.items()):
        valid = [r for r in rows if r["status"] == "valid"]
        should = rows[0]["should_trigger"]
        triggers = sum(r["target_triggered"] for r in valid)
        rate = triggers / len(valid) if valid else None
        if len(valid) < minimum_valid or rate is None:
            verdict = "insufficient_valid_attempts"
        elif should:
            verdict = "pass" if rate > 0.5 else "fail"
        else:
            verdict = "pass" if rate < 0.5 else "fail"
        summary.append(
            {
                "query_id": query_id,
                "skill": rows[0]["skill"],
                "should_trigger": should,
                "attempts": len(rows),
                "valid_attempts": len(valid),
                "invalid_attempts": len(rows) - len(valid),
                "trigger_rate": rate,
                "other_skills_loaded": sorted(
                    {
                        s
                        for r in valid
                        for s in r["invoked_skills"]
                        if s != rows[0]["skill"]
                    }
                ),
                "verdict": verdict,
            }
        )
    return summary


def estimate(
    entries: list[dict[str, Any]], repeat: int, concurrency: int
) -> dict[str, Any]:
    runs = len(entries) * repeat
    return {
        "queries": len(entries),
        "runs": runs,
        "concurrency": concurrency,
        "assumed_seconds_per_run": OBSERVED_SECONDS_PER_RUN,
        "estimated_minutes": round(
            runs * OBSERVED_SECONDS_PER_RUN / concurrency / 60, 1
        ),
    }


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cli.add_argument(
        "--skills", nargs="+", required=True, help="Skills whose queries run"
    )
    cli.add_argument("--queries-per-class", type=int, default=2)
    cli.add_argument("--dataset", default="validation_queries.json")
    cli.add_argument("--repeat", type=int, default=3)
    cli.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    cli.add_argument("--model", default=DEFAULT_MODEL)
    cli.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    cli.add_argument(
        "--product-archive",
        type=Path,
        help="tar archive of the product source placed in the workspace",
    )
    cli.add_argument("--concurrency", type=int, default=3)
    cli.add_argument(
        "--credentials",
        type=Path,
        default=Path.home() / ".claude" / ".credentials.json",
    )
    cli.add_argument("--out", type=Path)
    cli.add_argument(
        "--estimate", action="store_true", help="print the run count and exit"
    )
    args = cli.parse_args()

    unknown = sorted(set(args.skills) - set(repository_skills()))
    if unknown:
        print(f"unknown skills: {unknown}", file=sys.stderr)
        return 2
    entries = select_queries(args.skills, args.queries_per_class, dataset=args.dataset)
    plan = estimate(entries, args.repeat, args.concurrency)
    print(json.dumps(plan, ensure_ascii=False))
    if args.estimate:
        return 0
    if args.out is None:
        print("--out is required to run", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        workdir = base / "workspace"
        workdir.mkdir()
        loaded = build_workspace(workdir)
        if args.product_archive is not None:
            product = workdir / "product"
            product.mkdir()
            subprocess.run(
                ["tar", "-xf", str(args.product_archive), "-C", str(product)],
                check=True,
            )
        config = make_config_dir(base, args.credentials)
        jobs = [(entry, n) for entry in entries for n in range(1, args.repeat + 1)]
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            attempts = list(
                pool.map(
                    lambda job: run_attempt(
                        job[0],
                        job[1],
                        workdir=workdir,
                        config_dir=config,
                        model=args.model,
                        timeout=args.timeout,
                        max_turns=args.max_turns,
                    ),
                    jobs,
                )
            )
    summary = aggregate(attempts)
    args.out.write_text(
        json.dumps(
            {
                "model": args.model,
                "max_turns": args.max_turns,
                "product_archive": str(args.product_archive)
                if args.product_archive
                else None,
                "skills_available": loaded,
                "plan": plan,
                "attempts": attempts,
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    failed = [s for s in summary if s["verdict"] != "pass"]
    print(f"queries={len(summary)} not_passed={len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
