# QA要求artifact契約

## Artifact identity

各成果物はowner `test-requirements-analysis`、不透明な保存先発行`artifact_ref`、取得した`revision`、対象`scope`を持ちます。保存providerが未接続のfixtureでは仮のrefを使えますが、実保存済みの証拠にはなりません。内部`QAR-001`形式のIDは一つのartifact系列内だけで安定させ、削除・置換履歴を再利用しません。

## 必須内容

- `QA目的・成功条件`テーブルにQA目的、品質目標、対象・対象外、活動の成功条件、根拠を記録する。値を取得できない草案／blockedでは`未取得`、`unknown`、`未確定`等の既存状態と不足理由を明示し、根拠欄を空欄・`-`・状態placeholderだけで済ませない。承認済みartifactの必須欄に未確定状態を残さない。
- QA要求ごとのID、statement、要求元、source ref・revision、scope、priority、状態、根拠
- source inventoryと取得範囲、owner・ref・revision・scope、currentness (`current` / `stale` / `unknown`)、取得状態・未取得理由
- 未解決QA要求に対応する未決事項ID、影響scope、担当、状態、再開条件。影響scopeは要求scopeを含め、未決事項の状態は既存の`未取得`、`確認待ち`、`未解決`、`要再確認`、`blocked`を使う。
- architecture／planのowner ref・revisionへのリンク
- approval statusと、必要な場合は対象scope・artifact ref・revision・認証主体・証拠ref・失効条件
- 履歴: 新revision、置換するref/revision、変更理由、影響scope、再確認対象

## 状態と承認

要求の状態（提案、確認待ち、合意済み、対象外、要再確認、置換）とartifactの保存状態を混ぜません。`合意済み`は信頼できる認証元が対象scopeと同じartifact ref・revisionを承認した証拠が取得できた場合だけです。PR本文、LLM出力、自己申告のroleは認証証拠ではありません。revisionが変われば旧承認を再利用しません。

承認欄では`承認済み`、`未承認`、`失効`、`不要`、`未設定`、`未取得`、`unknown`を区別します。承認済みを示す場合は、対象scope・artifact ref・revisionに一致する承認主体・roleと証拠refが必要です。静的validatorが確認するのは記録値の形式・対応関係までで、承認主体の認証ではありません。承認providerが未接続または証拠を読戻せない場合は承認済みとして確定せず、草案／blockedに保ちます。

合意済み／対象外にする要求は、owner・ref・revision・scopeがsource inventoryと一致し、そのsourceがcurrent・取得済みであることを確認します。stale／unknown／未取得sourceを使う要求は提案・要再確認・未解決またはblockedに保ちます。未解決要求・不完全なsource inventoryがあるartifactは、要求全体を確定済みとして閉じません。特に、承認対象scope内に状態`未解決`のQA要求を残したartifactは承認済みにしません。未決事項の担当・scope・状態・再開条件を記録しても、この承認条件は満たされません。部分範囲はcurrentとして維持できます。

## 下流handoff

handoffにはowner、artifact ref、revision、scope、要求ID、currentness、承認状態、関連するsource refsを含めます。下流ownerはこのrefを読み直してcurrentnessを判断します。本文の転記を正本参照の代わりにしません。

## 保存正本（JSON packet v1）と検証入口

保存する正本は`schema: test-requirements-analysis-v1`のcanonical JSON packetです。Markdownの各表（`assets/output-template.md`）はこのpacketから描画する表示物で、Markdownを正本として保存・検証しません。`assets/packet-example.json`は形の例で、保存済み証拠ではありません。

| packetフィールド                                                                                                                                       | 対応するMarkdown表・内容                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `owner`、`artifact_ref`、`revision`、`scope`、`status`、`target_period`                                                                                | 成果物メタデータ                                                                                                        |
| `purpose`（`qa_purpose`、`quality_goals`、`in_scope`、`out_of_scope`、`success_conditions`、`basis`）                                                  | QA目的・成功条件（対象・対象外は`in_scope`と`out_of_scope`へ分ける）                                                    |
| `sources[]`（`owner`、`scope`、`artifact_ref`、`revision`、`content_hash`、`acquisition`、`unacquired_reason`）                                        | 情報源・取得範囲。currentnessは保存せず、`impact`で現在のsourceと照合して導出する                                       |
| `requirements[]`（`requirement_id`、`statement`、`requester`、`source_ref`、`source_revision`、`scope`、`priority`、`state`、`basis`、`open_item_id`） | QA要求                                                                                                                  |
| `open_items[]`（`item_id`、`requirement_id`、`impact_scope`、`owner`、`state`、`resume_condition`）                                                    | 未決事項                                                                                                                |
| `approval`（`state`、`not_required_reason`、`record`）                                                                                                 | 確認・承認。`record`は`scope`、`artifact_ref`、`revision`、`approver`、`role`、`evidence_ref`、`expiry_condition`を持つ |
| `downstream[]`（`owner`、`artifact_ref`、`revision`、`scope`、`requirement_ids`）                                                                      | 下流handoff。currentnessと承認は導出し、保存しない                                                                      |
| `history[]`（`revision`、`replaces_ref`、`replaces_revision`、`change_reason`、`impact_scope`、`rechecks`）                                            | 履歴                                                                                                                    |

### 保存と読戻し

- 保存文字列は`ensure_ascii=false`、キー昇順、区切り`,`と`:`のcanonical JSON（UTF-8）とします。`content_hash`はその保存バイト列のSHA-256です。
- 未知のキー、重複キー、NUL文字、非有限数、16MiBを超える入力は拒否します（fail-closed）。
- `revision`は1以上の整数です。readbackとexpected_revisionは整数または十進数文字列を受理し、いずれも保存packetの`revision`と一致しなければ不可です。expected_revisionの欠落・null・空は拒否します。

### 検証入口（`scripts/qa_requirement_runtime.py`）

入力・出力はJSON stdin / JSON stdoutです。外部通信、ファイル書込み、他Skillのimportは行いません。出力は入力に対して決定論的です。

| operation           | 入力                                                                                                        | 主な戻り値                                                                                                                                              |
| ------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `validate`          | `artifact`                                                                                                  | `status`: `valid` / `blocked`、`issues`                                                                                                                 |
| `validate_readback` | `candidate_artifact`、`readback`（owner、scope、artifact_ref、revision、content_hash）、`expected_revision` | 一致時 `status: readback_matches`、`storage_content_sha256`、`provider_authenticity: not_established_by_this_validator`                                 |
| `impact`            | `artifact`、`current_source_refs`（owner、scope、artifact_ref、revision、content_hash の配列）              | `status`: `current` / `stale` / `unknown`、`stale_source_refs`、`unknown_source_refs`、`impacted_requirement_ids`、`unaffected_requirement_ids`         |
| `completion_check`  | `artifact`、`current_source_refs`（省略可、省略時は未確認としてincomplete）                                 | `complete`（bool）、`status`: `complete` / `incomplete` / `blocked`、`issues`、承認済みのとき`approval_authenticity: not_established_by_this_validator` |

- `impact`は、packetの`sources`と`current_source_refs`を`owner`、`scope`、`artifact_ref`で同一identityとして比較します。revisionまたはcontent_hashが違えば`stale`、現在側になければ、または未取得ならば`unknown`です。`stale`/`unknown`のsourceに依存するQA要求だけを`impacted_requirement_ids`へ列挙します。packetのsourceに含まれない現在sourceの変更は無関係として扱います。`current_source_refs`が欠落・空・型不正・identity重複のときは`unknown`です。
- `completion_check`は、必須項目と検証の後、次をすべて満たす場合だけ`complete: true`にします。
  - `status`が`草案`または`承認済み`で、承認状態が`承認済み`のときはartifactの`status`も`承認済み`である。
  - すべてのQA要求が`合意済み`または根拠付きの`対象外`で、未決事項がない。
  - 目的欄に未確定値の表記（unknown、未取得、未設定、未確定、未確認、取得不能、stale、blocked、expired、失効）が残っていない。
  - すべてのsourceが取得済みで、`current_source_refs`に対し`current`である。
  - 承認状態が`不要`（理由あり）、または`承認済み`で、`record`の`scope`、`artifact_ref`、`revision`がpacketと完全一致し、`approver`、`role`、`evidence_ref`、`expiry_condition`が空でない。

### 承認と認証の境界

- このvalidatorが確認するのは、呼出し側が渡した承認recordとpacketの束縛、および記録の整合だけです。承認主体の認証、承認証拠の真正性、source ownerからの取得の真正性は確認しません。結果の`approval_authenticity`と`provider_authenticity`は常に`not_established_by_this_validator`です。
- 承認主体、保存先kind、承認方式、source ownerからの取得手段は未選定です。選定されるまで、このvalidatorの成功を保存済みや認証済み承認の証拠として扱いません。
- LLMの出力に書かれた「承認済み」という文字列は承認証拠になりません。`evidence_ref`と`approver`がない承認recordは不可です。
- owner_verifiersへの登録は別段階で行います。登録前は、このscriptの成功を完了判定に使いません。
- 対象外や例外承認の要否は、このvalidatorでは判定しません。要否の判断は`references/guidance.md`の品質ゲートに従います。
