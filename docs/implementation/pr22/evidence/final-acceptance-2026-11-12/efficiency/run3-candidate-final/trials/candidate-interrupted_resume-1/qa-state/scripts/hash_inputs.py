#!/usr/bin/env python3
"""読み取り専用: 仕様入力のsha256先頭12桁を計算し、01-spec-analysis.mdの記録と照合する。

製品ファイルは変更しない。出力はJSONのみ。
"""

import hashlib
import json
import os

WS = "<scratchpad>/eff7/workspaces/candidate-interrupted_resume-1"

# 01-spec-analysis.md の情報源一覧に記録された先頭12桁（未ハッシュは None）
RECORDED = {
    "product/docs/spec/features/cart.md": "385777e56a0d",
    "product/docs/spec/roles-and-permissions.md": "519731749c55",
    "product/docs/spec/state-and-scenarios.md": "ccd0cab4b0bd",
    "product/docs/spec/product-scope.md": "23508ebe243d",
    "product/docs/spec/ui-ux-contract.md": "ac9b86d99ff6",
    "product/docs/spec/unresolved-specifications.md": "c3ac09d0f145",
    "product/docs/spec/known-deviations.md": "518d110c069d",
    "product/docs/spec/features/checkout-and-payment.md": "9877302a255e",
    "product/docs/spec/features/authentication.md": "3334ecd7b5fb",
    "product/docs/spec/features/storefront.md": None,
    "product/docs/03_domain/business_rules.md": "8fe29aa8a481",
    "product/docs/12_quality/acceptance_criteria.md": "cb057739f878",
    "product/docs/12_quality/requirements_traceability.md": "3ad9acafa315",
}


def main():
    result = []
    for rel, recorded in RECORDED.items():
        path = os.path.join(WS, rel)
        if not os.path.isfile(path):
            result.append({"path": rel, "status": "missing"})
            continue
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()[:12]
        if recorded is None:
            status = "not_recorded"
        elif digest == recorded:
            status = "same"
        else:
            status = "changed"
        result.append(
            {"path": rel, "sha256_12": digest, "recorded": recorded, "status": status}
        )
    summary = {}
    for r in result:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    print(
        json.dumps({"summary": summary, "files": result}, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
