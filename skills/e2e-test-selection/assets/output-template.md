# E2E対象選定

## 判断範囲

- selection ref / revision:
- current revision digest: `sha256:<64 lowercase hex>`
- current change reason:
- 自動化目的:
- 候補母集団と完全性:
- source refs / revisions / currentness (`REF@revision=current|stale|unknown`):
- retired candidate IDs / 理由:
- 対象外:
- blocker / 再開条件:
- 選定状態: ready / unresolved / blocked

## 候補と判断

候補が0件の場合、`population_complete=false`と具体的blockerがある未完了状態だけを記録します。候補行や採否を推測で作らず、選定状態をblockedとして再開条件を残します。

| Candidate ID / key | feature / item / condition refs | E2E候補範囲 | decision | 技術非依存の価値・根拠 | source revision | 保留・重複・制約 |
| ------------------ | ------------------------------- | ----------- | -------- | ---------------------- | --------------- | ---------------- |
|                    |                                 |             |          |                        |                 |                  |

## 履歴

履歴にはcurrent revisionより前のsnapshotをrevision順にすべて記録します。初回revisionでは履歴行を作りません。過去にretireしたcandidateは後続snapshotにも理由付きで残します。

| revision | previous revision | candidate IDs / keys | decisions / rationale | source refs / revisions / currentness | retired candidate IDs / reason | change reason | revision digest |
| -------- | ----------------- | -------------------- | --------------------- | ------------------------------------- | ------------------------------ | ------------- | --------------- |
|          |                   |                      |                       |                                       |                                |               |                 |

各履歴行はそのrevisionの候補判断・理由と、candidateが参照したsourceのrevision/currentnessを復元できる完全snapshotです。過去snapshotにも現行入力と同じ候補母集団・blocker条件を適用し、母集団が不完全なのにblockerがないsnapshotは、digestを再計算した場合も拒否します。`revision digest`には、そのrevisionのdecision・rationale・source・retirement・change reasonを含みます。digestが欠けている、またはsnapshotと一致しない場合は推測せず、history incomplete／改変としてblockedを記録します。digestは整合性確認であり、保存先の真正性を証明しないため、実readbackを確認します。

## 下流への受渡し

- 選定refを利用するconsumer:
- 直接TC指定／E2E直接実行との区別:
- `e2e-test-inspection`へ渡す選定対象:
- 未統合owner fixture / PR #22確認事項:
