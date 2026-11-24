import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "qa-state", "workflow-state.json")


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def main() -> None:
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    print("== recorded vs current ==")
    for key, rec in state["input_revisions"].items():
        p = os.path.join(ROOT, rec["path"])
        if not os.path.exists(p):
            print(f"{key}\tMISSING\t{rec['path']}")
            continue
        with open(p, "rb") as f:
            cur = sha(f.read())
        status = "SAME" if cur == rec["sha256"] else "CHANGED"
        print(f"{key}\t{status}\t{rec['path']}\t{cur}")
    # Reconstruct pre-change cart.md (reverse of diff line 9) and compare with recorded hash
    cart = os.path.join(ROOT, "product/docs/spec/features/cart.md")
    with open(cart, "rb") as f:
        raw = f.read()
    old = raw.replace("「50」のうち".encode("utf-8"), "「99」のうち".encode("utf-8"), 1)
    print("== reverse-applied cart.md ==")
    print("reconstructed_pre_image_sha\t" + sha(old))
    print("recorded_SRC-001\t" + state["input_revisions"]["SRC-001"]["sha256"])
    print(
        "pre_image_matches_recorded\t"
        + str(sha(old) == state["input_revisions"]["SRC-001"]["sha256"])
    )
    print("crlf_in_file\t" + str(b"\r\n" in raw))


if __name__ == "__main__":
    main()
