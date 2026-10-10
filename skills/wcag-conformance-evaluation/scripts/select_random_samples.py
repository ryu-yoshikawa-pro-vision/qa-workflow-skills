"""Non-deterministic finite-inventory selector; deliberately outside Machine Runtime."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPT_DIR))
from sampling import SamplingError, select_random_candidates


def main() -> int:
    try:
        request=json.load(sys.stdin)
        if not isinstance(request,dict) or set(request)!={"candidates","structured_refs","target_count","excluded_refs"}:
            raise SamplingError("random selection input schema mismatch")
        result=select_random_candidates(candidates=request["candidates"],
            structured_refs=request["structured_refs"],target_count=request["target_count"],
            excluded_refs=request["excluded_refs"])
        sys.stdout.write(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
        return 0
    except (json.JSONDecodeError,SamplingError,TypeError,KeyError) as exc:
        sys.stderr.write(f"random selection failed: {exc}\n")
        return 2


if __name__=="__main__":
    raise SystemExit(main())
