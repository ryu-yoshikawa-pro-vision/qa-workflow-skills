"""Project a UI target package into one file for repository eval runners."""

from __future__ import annotations

import argparse
import re
import stat
import sys
from pathlib import Path, PurePosixPath

VERSION_RE = re.compile(r"^v[0-9]{2,}$")
EXTENSION_FILE_RE = re.compile(
    r"^(?P<number>1[0-9]|[2-9][0-9]+)_[a-z0-9]+(?:-[a-z0-9]+)*\.md$"
)
CORE_ORDER = (
    "README.md",
    "00_scope_and_context.md",
    "01_ui_structure_and_navigation.md",
    "02_behavior_and_business_rules.md",
    "03_fields_and_validation.md",
    "04_flows_and_data.md",
    "05_notifications_and_external_interactions.md",
    "06_spec_inconsistencies_and_pending.md",
    "07_current_unknowns.md",
    "08_repository_implementation_status.md",
    "09_authority_and_traceability.md",
)
REQUIRED_FILES = {
    "README.md",
    "00_scope_and_context.md",
    "01_ui_structure_and_navigation.md",
    "02_behavior_and_business_rules.md",
    "06_spec_inconsistencies_and_pending.md",
    "07_current_unknowns.md",
    "09_authority_and_traceability.md",
    "CHANGELOG.md",
}


class ProjectionError(ValueError):
    """A package cannot be safely projected for evaluation."""


def _canonical_key(relative: str) -> tuple[int, int, str]:
    if relative == "README.md":
        return (0, 0, relative)
    if relative in CORE_ORDER:
        return (1, CORE_ORDER.index(relative), relative)
    if relative == "CHANGELOG.md":
        return (3, 0, relative)
    match = EXTENSION_FILE_RE.fullmatch(relative)
    if match is None:
        raise ProjectionError(f"MANIFEST contains an unknown payload file: {relative}")
    return (2, int(match.group("number")), relative)


def _read_utf8(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ProjectionError(f"package file is unreadable: {path.name}") from exc
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProjectionError(f"package file is not UTF-8: {path.name}") from exc


def _manifest(manifest_text: str) -> tuple[str, list[str]]:
    schema_match = re.search(
        r"^Package Schema Version:\s*(\S+)\s*$", manifest_text, re.MULTILINE
    )
    version_match = re.search(
        r"^Package Version:\s*(\S+)\s*$", manifest_text, re.MULTILINE
    )
    if (
        schema_match is None
        or schema_match.group(1) != "ui-target-v1"
        or version_match is None
        or not VERSION_RE.fullmatch(version_match.group(1))
    ):
        raise ProjectionError("MANIFEST package schema or version is invalid")

    lines = manifest_text.splitlines()
    table_headers = [
        index
        for index, line in enumerate(lines)
        if line.strip() == "| 順序 | ファイル | SHA-256 |"
    ]
    if len(table_headers) != 1:
        raise ProjectionError("MANIFEST must contain one canonical package file table")
    if (
        table_headers[0] + 1 >= len(lines)
        or re.fullmatch(
            r"\|\s*:?-{3,}:?\s*\|\s*:?-{3,}:?\s*\|\s*:?-{3,}:?\s*\|",
            lines[table_headers[0] + 1].strip(),
        )
        is None
    ):
        raise ProjectionError("MANIFEST package file table separator is invalid")
    start = table_headers[0] + 2
    paths: list[str] = []
    extension_numbers: set[int] = set()
    expected_order = 1
    for line in lines[start:]:
        if not line.strip().startswith("|"):
            break
        match = re.fullmatch(
            r"\|\s*([0-9]+)\s*\|\s*([^|]+?)\s*\|\s*([0-9a-f]{64})\s*\|",
            line.strip(),
        )
        if match is None or int(match.group(1)) != expected_order:
            raise ProjectionError("MANIFEST package file rows are invalid or unordered")
        relative = match.group(2).strip()
        _validate_relative(relative)
        if relative not in CORE_ORDER and relative != "CHANGELOG.md":
            extension_match = EXTENSION_FILE_RE.fullmatch(relative)
            if extension_match is None:
                raise ProjectionError("MANIFEST contains an unknown payload file")
            extension_number = int(extension_match.group("number"))
            if extension_number in extension_numbers:
                raise ProjectionError(
                    "MANIFEST contains duplicate extension file numbers"
                )
            extension_numbers.add(extension_number)
        paths.append(relative)
        expected_order += 1
    if not paths or len(set(paths)) != len(paths):
        raise ProjectionError("MANIFEST package file paths are empty or duplicated")
    if paths != sorted(paths, key=_canonical_key):
        raise ProjectionError("MANIFEST package file paths are not canonical order")
    if not REQUIRED_FILES.issubset(paths):
        raise ProjectionError("MANIFEST omits a required core package file")
    return version_match.group(1), paths


def _validate_relative(relative: str) -> PurePosixPath:
    path = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != relative
    ):
        raise ProjectionError("MANIFEST contains an unsafe relative path")
    return path


def _package_files(root: Path, paths: list[str]) -> dict[str, Path]:
    allowed = set(paths) | {"MANIFEST.md"}
    actual: set[str] = set()
    for candidate in root.rglob("*"):
        try:
            mode = candidate.lstat().st_mode
        except OSError as exc:
            raise ProjectionError("package contains an unreadable path") from exc
        if stat.S_ISLNK(mode):
            raise ProjectionError("package symlinks are not allowed")
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ProjectionError("package contains a non-regular file")
        relative = candidate.relative_to(root).as_posix()
        if relative not in allowed:
            raise ProjectionError("package files differ from MANIFEST")
        actual.add(relative)
    if actual != allowed:
        raise ProjectionError("package files differ from MANIFEST")

    result: dict[str, Path] = {}
    for relative in allowed:
        safe_relative = _validate_relative(relative)
        candidate = root.joinpath(*safe_relative.parts)
        current = root
        for part in safe_relative.parts:
            current = current / part
            if current.is_symlink():
                raise ProjectionError("package symlinks are not allowed")
        try:
            candidate.resolve(strict=True).relative_to(root)
        except (OSError, ValueError) as exc:
            raise ProjectionError("package path escapes the package root") from exc
        result[relative] = candidate
    return result


def _current_change_summary(text: str, current_version: str) -> str:
    lines = text.splitlines()
    version_heading = re.compile(r"^##\s+" + re.escape(current_version) + r"\s*$")
    starts = [
        index for index, line in enumerate(lines) if version_heading.fullmatch(line)
    ]
    if len(starts) != 1:
        raise ProjectionError(
            "CHANGELOG current package version is missing or duplicated"
        )
    start = starts[0] + 1
    end = next(
        (
            index
            for index in range(start, len(lines))
            if re.match(r"^##\s+", lines[index])
        ),
        len(lines),
    )
    section = lines[start:end]
    summary_heading = [
        index for index, line in enumerate(section) if line.strip() == "### 変更概要"
    ]
    if len(summary_heading) != 1:
        raise ProjectionError("CHANGELOG current version needs one 変更概要 section")
    summary_start = summary_heading[0] + 1
    summary_end = next(
        (
            index
            for index in range(summary_start, len(section))
            if re.match(r"^#{1,6}\s+", section[index])
        ),
        len(section),
    )
    summary = "\n".join(section[summary_start:summary_end]).strip()
    if not summary:
        raise ProjectionError("CHANGELOG current 変更概要 is empty")
    return summary


def _current_stable_id_changes(text: str, current_version: str) -> str:
    lines = text.splitlines()
    version_heading = re.compile(r"^##\s+" + re.escape(current_version) + r"\s*$")
    starts = [
        index for index, line in enumerate(lines) if version_heading.fullmatch(line)
    ]
    if len(starts) != 1:
        raise ProjectionError(
            "CHANGELOG current package version is missing or duplicated"
        )
    start = starts[0] + 1
    end = next(
        (
            index
            for index in range(start, len(lines))
            if re.match(r"^##\s+", lines[index])
        ),
        len(lines),
    )
    section = lines[start:end]
    headings = [
        index
        for index, line in enumerate(section)
        if line.strip() == "### Stable ID changes"
    ]
    if len(headings) != 1:
        raise ProjectionError(
            "CHANGELOG current version needs one Stable ID changes section"
        )
    body_start = headings[0] + 1
    body_end = next(
        (
            index
            for index in range(body_start, len(section))
            if re.match(r"^#{1,6}\s+", section[index])
        ),
        len(section),
    )
    changes = "\n".join(section[body_start:body_end]).strip()
    if not changes:
        raise ProjectionError("CHANGELOG current Stable ID changes is empty")
    return changes


def project(package_root: str | Path, mode: str) -> str:
    if mode not in {"semantic", "deterministic"}:
        raise ProjectionError("projection mode must be semantic or deterministic")
    supplied_root = Path(package_root)
    if supplied_root.is_symlink():
        raise ProjectionError("package root symlinks are not allowed")
    try:
        root = supplied_root.resolve(strict=True)
    except OSError as exc:
        raise ProjectionError("package root is missing or unreadable") from exc
    if not root.is_dir():
        raise ProjectionError("package root must be a directory")

    manifest_path = root / "MANIFEST.md"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ProjectionError("MANIFEST.md is missing or unsafe")
    manifest_text = _read_utf8(manifest_path)
    current_version, payload_paths = _manifest(manifest_text)
    package_paths = _package_files(root, payload_paths)

    content: dict[str, str] = {}
    for relative in payload_paths:
        content[relative] = _read_utf8(package_paths[relative])

    selected_paths = (
        [path for path in payload_paths if path != "CHANGELOG.md"]
        if mode == "semantic"
        else payload_paths
    )
    chunks = [
        f"<!-- FILE: {relative} -->\n{content[relative]}" for relative in selected_paths
    ]
    if mode == "semantic":
        summary = _current_change_summary(content["CHANGELOG.md"], current_version)
        chunks.append("<!-- CONTROL: CHANGELOG.current_change_summary -->\n" + summary)
        stable_id_changes = _current_stable_id_changes(
            content["CHANGELOG.md"], current_version
        )
        chunks.append(
            "<!-- CONTROL: CHANGELOG.current_stable_id_changes -->\n"
            + stable_id_changes
        )
    else:
        chunks.append(f"<!-- FILE: MANIFEST.md -->\n{manifest_text}")
    return "\n\n".join(chunks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projection", required=True, choices=("semantic", "deterministic")
    )
    parser.add_argument("package_root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        sys.stdout.buffer.write(
            project(args.package_root, args.projection).encode("utf-8")
        )
        return 0
    except ProjectionError as exc:
        sys.stderr.write(f"ui_target_projection: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
