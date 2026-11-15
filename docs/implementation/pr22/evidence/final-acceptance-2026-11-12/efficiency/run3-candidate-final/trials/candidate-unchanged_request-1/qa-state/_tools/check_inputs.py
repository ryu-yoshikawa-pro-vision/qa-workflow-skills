"""workflow-state.json の input_revisions と現在のファイルsha256を比較する（読取専用）。

使い方: python3 <絶対path>/check_inputs.py <workspace_root> <workflow-state.json の絶対path>
"""

import hashlib
import json
import os
import sys


def main() -> int:
    root = sys.argv[1]
    state_path = sys.argv[2]
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    results = []
    for src_id, rec in state["input_revisions"].items():
        path = os.path.join(root, rec["path"])
        if not os.path.isfile(path):
            results.append({"id": src_id, "path": rec["path"], "status": "missing"})
            continue
        with open(path, "rb") as f:
            digest = "sha256:" + hashlib.sha256(f.read()).hexdigest()
        status = "same" if digest == rec["sha256"] else "changed"
        results.append(
            {"id": src_id, "path": rec["path"], "status": status, "current": digest}
        )
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    print(
        json.dumps({"summary": summary, "items": results}, ensure_ascii=False, indent=2)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
