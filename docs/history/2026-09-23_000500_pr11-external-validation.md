# PR #11 外部検証の追記

2026-09-23 JST、PR #11の未確認だった外部検証を実施した。

- 既存`semantic/run.py`のrunner protocolに外部Judge commandを接続し、本Planの追加・更新case 24件を評価した。`test-analysis` 5件、`test-condition-design` 12件、`test-case-design` 更新1件、`adversarial-review` 6件で、24/24 PASSだった。
- `codex exec`による実Agent runtime smokeを`test-analysis`と`test-condition-design`で実行した。Python 3.11.9、stdout envelope strict parse、Machine Entity / runtime result採用、Markdown保存・再読込、semantic dependency preflight、同一入力のcurrent script再実行、fingerprint / payload一致、secret値非保存を確認した。
- Python 3.11.9通常レイアウトでcompileall、runtime unit 135、shared deterministic 12、repository deterministic 54、semantic shared 27（skip 2）、semantic repository 4、trigger 1、semantic dataset 14 Skill / 51 case、deterministic output 28 caseをPASSした。
- 最初に用いたembeddable Python 3.11は`._pth`によるSkill-local import不成立でruntime unitが失敗したため、通常レイアウトの一時Python 3.11.9へ切り替えた。これは環境差であり、source実装の変更は行っていない。
