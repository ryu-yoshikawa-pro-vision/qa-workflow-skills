from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MarkdownTable:
    section: str
    headers: list[str]
    rows: list[dict[str, str]]


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    # Canonical templates do not require escaped pipes in cells.
    return [cell.strip() for cell in line.split("|")]


def _is_separator(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells)


def parse_tables(text: str) -> list[MarkdownTable]:
    lines = text.splitlines()
    tables: list[MarkdownTable] = []
    section = ""
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            section = stripped.lstrip("#").strip()
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and _is_separator(lines[i + 1]):
            headers = _split_row(lines[i])
            rows: list[dict[str, str]] = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = _split_row(lines[i])
                if len(cells) < len(headers):
                    cells.extend([""] * (len(headers) - len(cells)))
                rows.append(dict(zip(headers, cells[: len(headers)])))
                i += 1
            tables.append(MarkdownTable(section=section, headers=headers, rows=rows))
            continue
        i += 1
    return tables


def find_table(
    tables: list[MarkdownTable],
    *,
    section_contains: str | None = None,
    required_headers: tuple[str, ...] = (),
) -> MarkdownTable | None:
    for table in tables:
        if section_contains and section_contains not in table.section:
            continue
        if all(h in table.headers for h in required_headers):
            return table
    return None


def parse_bullets(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*-\s*([^:：]+)[:：]\s*(.*?)\s*$", line)
        if m:
            result[m.group(1).strip()] = m.group(2).strip()
    return result
