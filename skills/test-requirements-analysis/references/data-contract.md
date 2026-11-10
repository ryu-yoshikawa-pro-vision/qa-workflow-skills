# QA要求artifact契約

## Artifact identity

各成果物はowner `test-requirements-analysis`、不透明な保存先発行`artifact_ref`、取得した`revision`、対象`scope`を持ちます。保存providerが未接続のfixtureでは仮のrefを使えますが、実保存済みの証拠にはなりません。内部`QAR-001`形式のIDは一つのartifact系列内だけで安定させ、削除・置換履歴を再利用しません。

## 必須内容

- `QA目的・成功条件`テーブルにQA目的、品質目標、対象・対象外、活動の成功条件、根拠を記録する。値を取得できない草案／blockedでは`未取得`、`unknown`、`未確定`等の既存状態と理由を明示し、空欄や`-`で代用しない。承認済みartifactの必須欄に未確定状態を残さない。
- QA要求ごとのID、statement、要求元、source ref・revision、scope、priority、状態、根拠
- source inventoryと取得範囲、owner・ref・revision・scope、currentness (`current` / `stale` / `unknown`)、取得状態・未取得理由
- 未解決QA要求に対応する未決事項ID、影響scope、担当、状態、再開条件。影響scopeは要求scopeを含め、未決事項の状態は既存の`未取得`、`確認待ち`、`未解決`、`要再確認`、`blocked`を使う。
- architecture／planのowner ref・revisionへのリンク
- approval statusと、必要な場合は対象scope・artifact ref・revision・認証主体・証拠ref・失効条件
- 履歴: 新revision、置換するref/revision、変更理由、影響scope、再確認対象

## 状態と承認

要求の状態（提案、確認待ち、合意済み、対象外、要再確認、置換）とartifactの保存状態を混ぜません。`合意済み`は信頼できる認証元が対象scopeと同じartifact ref・revisionを承認した証拠が取得できた場合だけです。PR本文、LLM出力、自己申告のroleは認証証拠ではありません。revisionが変われば旧承認を再利用しません。

承認欄では`承認済み`、`未承認`、`失効`、`不要`、`未設定`、`未取得`、`unknown`を区別します。承認済みを示す場合は、対象scope・artifact ref・revisionに一致する承認主体・roleと証拠refが必要です。静的validatorが確認するのは記録値の形式・対応関係までで、承認主体の認証ではありません。承認providerが未接続または証拠を読戻せない場合は承認済みとして確定せず、草案／blockedに保ちます。

合意済み／対象外にする要求は、owner・ref・revision・scopeがsource inventoryと一致し、そのsourceがcurrent・取得済みであることを確認します。stale／unknown／未取得sourceを使う要求は提案・要再確認・未解決またはblockedに保ちます。未解決要求・不完全なsource inventoryがあるartifactは、要求全体を確定済みとして閉じません。部分範囲はcurrentとして維持できます。

## 下流handoff

handoffにはowner、artifact ref、revision、scope、要求ID、currentness、承認状態、関連するsource refsを含めます。下流ownerはこのrefを読み直してcurrentnessを判断します。本文の転記を正本参照の代わりにしません。
