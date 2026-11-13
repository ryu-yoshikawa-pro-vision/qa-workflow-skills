"""入力成果物（仕様書）のsha256とバイト数を表示する補助スクリプト。

使い方: python3 <絶対path>/fingerprint_inputs.py <product直下からの相対path> ...
読み取りのみ。製品コード・仕様書は変更しない。
"""

import hashlib
import os
import sys

PRODUCT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "product")
)

for rel in sys.argv[1:]:
    path = os.path.join(PRODUCT_ROOT, rel)
    with open(path, "rb") as fh:
        data = fh.read()
    print(f"{hashlib.sha256(data).hexdigest()}  {len(data):>7}  {rel}")
