# E2E対象選定

## 判断範囲

- selection ref / revision:
- current change reason:
- 自動化目的:
- 候補母集団と完全性:
- source refs / revisions / currentness (`REF@revision=current|stale|unknown`):
- retired candidate IDs / 理由:
- 対象外:
- blocker / 再開条件:
- 選定状態: ready / unresolved / blocked

## 候補と判断

| Candidate ID / key | feature / item / condition refs | E2E候補範囲 | decision | 技術非依存の価値・根拠 | source revision | 保留・重複・制約 |
| ------------------ | ------------------------------- | ----------- | -------- | ---------------------- | --------------- | ---------------- |
|                    |                                 |             |          |                        |                 |                  |

## 履歴

履歴にはcurrent revisionより前のsnapshotをrevision順にすべて記録します。初回revisionでは履歴行を作りません。過去にretireしたcandidateは後続snapshotにも理由付きで残します。

| revision | previous revision | candidate IDs / keys | source refs / revisions / currentness | retired candidate IDs / reason | change reason |
| -------- | ----------------- | -------------------- | ------------------------------------- | ------------------------------ | ------------- |
|          |                   |                      |                                       |                                |               |

## 下流への受渡し

- 選定refを利用するconsumer:
- 直接TC指定／E2E直接実行との区別:
- `e2e-test-inspection`へ渡す選定対象:
- 未統合owner fixture / PR #22確認事項:
