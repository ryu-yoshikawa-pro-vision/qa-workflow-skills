"""カート機能QAの入力revision（SHA-256）を計算し、JSONとして出力する。

使い方: python3 -I <この絶対パス> [--write]
--write を付けた場合のみ qa-state/input-revisions.json へ保存する。
製品ディレクトリへは書き込まない（読み取りのみ）。
"""

import hashlib
import json
import os
import sys

WS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PRODUCT = os.path.join(WS, "product")
STATE = os.path.join(WS, "qa-state")

TARGETS = [
    "docs/spec/features/cart.md",
    "docs/spec/README.md",
    "docs/spec/change-process.md",
    "docs/spec/known-deviations.md",
    "docs/spec/unresolved-specifications.md",
    "docs/spec/state-and-scenarios.md",
    "docs/spec/roles-and-permissions.md",
    "docs/spec/features/authentication.md",
    "docs/spec/features/checkout-and-payment.md",
    "docs/spec/features/storefront.md",
    "docs/spec/ui-ux-contract.md",
    "docs/spec/screen-catalog.md",
    "docs/03_domain/business_rules.md",
    "docs/01_requirements/functional_requirements.md",
]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    result = {
        "product_commit_claimed": "2a8bcf57",
        "product_git_repository": os.path.isdir(os.path.join(PRODUCT, ".git")),
        "files": {},
    }
    for rel in TARGETS:
        p = os.path.join(PRODUCT, rel.replace("/", os.sep))
        if os.path.isfile(p):
            result["files"][rel] = {"sha256": sha256_of(p), "bytes": os.path.getsize(p)}
        else:
            result["files"][rel] = {"missing": True}
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if "--write" in sys.argv:
        os.makedirs(STATE, exist_ok=True)
        with open(
            os.path.join(STATE, "input-revisions.json"), "w", encoding="utf-8"
        ) as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
