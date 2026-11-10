# E2E対象選定 判断基準

## 選定の目的

UIを通る一連の利用者価値を自動で繰り返し確認する価値があるか判断します。選定はテスト層の置き換えではなく、必要な層を保った上での追加判断です。API／component等で十分な仕様保証、手動確認が必要な探索、頻繁に変わるUIに起因する保守負担も候補ごとに考慮します。

## 候補とsource

- feature、test item、共通condition候補、Authority、既存TC／E2Eをsource refとして明記し、revisionまたは同等のimmutable revision tokenを記録します。
- 候補集合の境界と母集団が閉じているか示します。全候補を列挙できない場合は`unresolved`または`blocked`とし、100%選定済みと表現しません。
- D等のownerがまだ実装・統合されていない場合は固定fixtureを利用できますが、実owner artifactのcurrentnessやPR #22の接続済み証拠とは扱いません。
- Authorityやsourceの内容と選定結果のrevisionが一致することを確認します。未知・stale・revision不明のsourceを根拠にreadyとしません。

## 判断要素

- 主要な利用者／業務経路をUIから最後まで通す必要性
- リリースごと、変更ごと、または継続的に繰り返す確認の価値
- 複数機能・role・外部境界を通る統合価値と、下位テストへ切り分けられる範囲
- UIを通さない場合に見落とすリスクと、UI経路を追加することで得る証拠
- 既存TC、既存E2E、手動または他層の自動確認との重複
- 環境・データの安定性などの価値を左右する既知制約（実装可能性やlocatorの詳細は含めない）

## decisionと状態

- `selected`: 技術非依存の価値と理由があり、対象scopeがcurrent。
- `not_selected`: UI経路を加える価値が低い、他のtest levelで十分、または重複する等の理由がある。
- `deferred`: 判断に必要な情報・優先順位が未確定。完了選定に数えない。
- `blocked`: 必須source、Authority、母集団または上流判断が欠ける。原因と再開条件を残す。

`ready`は候補集合が完全で、全sourceがcurrent、すべての候補がselectedまたはnot_selectedの場合だけです。候補が全件not_selectedでも、その結論と理由が完全なら有効な選定です。候補がない場合は`population_complete=false`でない限り完了にしません。

候補がまだ列挙できない初回revisionは、`population_complete=false`かつ具体的な`blockers`がある場合に限り、候補0件のblocked selectionとして記録できます。候補0件かつblockerなし、または完全な母集団で候補0件のrecordは受け付けず、readyへ昇格させません。blocker解消後のrevisionではselection IDを維持し、前revisionの0件snapshot・digestをそのまま履歴に残し、新たに確定した候補へ採否を付けます。

## 履歴と再評価

selection IDは同じ選定対象を改訂する間維持し、revisionは単調増加させます。current revisionには`change_reason`と`current_revision_digest`を持たせ、revision 1から直前revisionまでの全snapshotを連続して記録します。各snapshotにはscope・母集団状態、全source ref/revision/currentness、候補ごとのID/key/decision/rationale/source refs、累積retirementを含め、直前runtimeが返した`revision_digest`を保持します。sourceの更新、feature/item/condition候補の追加・削除、Authorityや利用者価値の変化を理由付きで残します。変更が及ぶ候補だけ再評価し、影響しない候補の判定を維持できます。削除候補は削除したrevisionの`retired_candidates[]`と現行結果に理由付きで記録し、後続履歴から消さず、IDを再利用しません。保存済みdigestとsnapshotが一致しなければ改変として拒否します。digest自体は保存先の真正性を証明しないため、provider readbackの検証も必要です。

既存revision履歴にID/keyと変更理由しかなく、当時のdecision・rationale・source revision/currentnessまたはrevision digestを復元できない場合は、読取互換を保ったまま`history_complete=false`と`blocked`を返します。値やdigestを推測して埋めたり、同じselection IDのcurrent履歴として昇格させたりしません。ownerが正本snapshotを取得して完全な連続履歴を復元するか、明示的に独立した新selectionを開始した後に再開します。

## 旧test-analysis選定記録との互換性

- 旧`test-analysis`成果物の「E2E対象選定」表はlegacy記録として読み取り、既存validatorで検証できる状態を保ちます。上書き・削除・新形式への暗黙変換はしません。
- 旧表だけでは新しいselection ID、source revision/currentness、連続したrevision履歴を証明できません。`e2e-selection-v1`のcurrent recordやcurrentな採否判断として昇格・再利用しません。
- 旧表と新形式が併存する場合、source currentnessとreadbackを確認できる新形式recordを新規E2E選定の正本として扱い、旧表は過去記録として保持します。両者の候補や判断は自動でmergeしません。
- 既存legacy記録を同じselectionの改訂として継続する必要があるのに、安定ID・revision履歴・source対応を安全に解決できない場合は、対応関係を推測せずmigrationをblockedにします。独立した新規選定を依頼された場合は、current sourceと承認済みwriterから新しいidentityを得て再評価し、旧表を根拠付きの履歴参照として残します。

## 停止条件

- 目的・候補範囲が定義できず、選定母集団を作れない
- 判断に不可欠なcurrent Authorityまたはsource revisionを解決できない
- upstream選定者だけが決められるtest level・対象境界が未決
- 再利用selectionのcurrentnessやrevision履歴を確認できず、選定の再実行が安全でない

対象を分離できる場合は全体を止めず、該当candidateのみblocked／deferredとして残します。
