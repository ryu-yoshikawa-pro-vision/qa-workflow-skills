"""Read-only item owner-contract validator embedded in this isolated Skill."""

from __future__ import annotations

from typing import Any

from candidate_support import validate_item_artifact as _validate_item_artifact


def validate_item_artifact(value: Any) -> dict[str, Any]:
    """Use the byte-identical D item validator without a sibling Skill import."""
    return _validate_item_artifact(value)
