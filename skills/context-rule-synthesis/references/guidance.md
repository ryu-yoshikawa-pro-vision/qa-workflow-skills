# Context Rule Synthesis ガイダンス

## 1. 検索と入力負荷

1. 実行環境から渡された指定rootと許可範囲に対して、過去batch/candidate/runと既存ownerの検索入口から軽量投影を集めます。project/kindごとのrootを探索・選択・切替せず、root binding・owner/share・権限をAI入力から変更しません。
2. `context_artifacts.py`のprojectionまたはowner固有list/read helperでref/revision/hash、scope、短い主張/観察、属性、状態、鮮度、必要な根拠refだけを確認します。本文全件をAIへ渡しません。
3. 同義概念・表現ゆれ・関連操作・scope外発見も意味的に確認し、タグ不一致だけで除外しません。本文選択後に必要な範囲だけを実行環境が提供する読取入口から読み、保存revision/hash/Authorityを照合します。
4. QA Knowledgeの`read_root_entries`/`scan_knowledge_root`/lookup/currentness等は既存契約を使います。formal applicabilityを弱めません。中央index、embedding store、別DBは追加しません。
5. list/readが取得不能な対象はsnapshotの`unverifiable_sources`へ理由付きで残し、空集合と区別します。絞込みに必要な属性が得られない場合は追加読取または未確認にします。

## 2. identityとsnapshot

`operation_input`は操作種別、artifact ref/content hash/effective Authority fingerprintを対応付けた`input_sources[]`、取得可能性・認可/安全条件・未解決論点の合否必須性など再評価理由に関係する開始時条件を保持します。requested scope、analysis aspect、調査条件、environment/versionはrunの`requested_scope`へ一度だけ保存し、identity helperが`operation_input`と併せてhashします。秘密token、毎回変わる時刻、無関係なHEAD進行を含めません。追加取得・handoffで得た根拠はsnapshotを更新しても開始時operation identityを変えません。

snapshotは直接参照したSPEC/DEC/ASM/Knowledge/回答/調査・実装証拠ごとのref/revision/hash/authority fingerprintと検索条件を保持します。completeは列挙・検索・確認手順が完了した意味で、未知の根拠が絶対に存在しないという保証ではありません。過去revisionをreadbackできない場合、現在本文で当時の完了を代用しません。

## 3. 根拠と仮説

- `identity_key`はdomain、operation axis、rule kind、target scope kind、governing conditions、assertion polarity、normalized assertionで構成します。主張文の言い換えや検索tagだけで同一性を変えず、意味条件・極性が違う候補は分けます。
- 同じcomponent、同じdocument、同じ観察の再取得は独立性を増やしません。訂正前後は歴史として残しても別個の独立根拠ではありません。
- 1候補は1独立仮説です。管理者権限と復元不能性など競合説明は候補を分けて`competing_hypothesis`/`alternative`で関係付けます。
- evidence evaluationの正式値は`supports|counterexample|indeterminate|out_of_scope`です。`unobserved_ranges`は第五の非観察状態です。反例原因は`scope_difference|impl_bug_candidate|spec_change|observation_condition|hypothesis_error|unclassified`から選びます。
- `governing_conditions`と`applicability.cross_cutting_attributes`の構造を整合させます。意味的に属性が法則を限定するかはAIが確認し、固定辞書/スコアに委ねません。
- 同じsignalを別候補で別評価に使えます。source batchへ候補評価を書き戻しません。

## 4. Authorityと既存ownerのrouting

| 発見                                         | 候補状態・扱い                             | owner                                            |
| -------------------------------------------- | ------------------------------------------ | ------------------------------------------------ |
| 有効SPEC/DECが全範囲を裏付け、実装一致       | resolved、SPEC/DEC、conforms               | spec-analysis                                    |
| 有効SPEC/DECが全範囲を裏付け、実装未確認     | resolved、unverified                       | spec-analysis、必要な実装確認Skill               |
| 有効SPEC/DECと既存FAIL/Findingが不一致を確認 | resolved、confirmed_mismatch               | defect-management。仕様質問へ戻さない            |
| コード推論のみで不一致を疑う                 | resolvedのAuthorityは維持、実装unverified  | 対象調査Skillまたはexploratory-testing           |
| Authorityが一部だけ裏付ける                  | investigating/partial、または安全にsplit   | spec-analysisと残範囲調査                        |
| 承認済みASM/Project Contextによる暫定解決    | resolved、正式SPECと区別                   | project-context/spec-analysis                    |
| 実装・探索観察だけ、正式仕様なし             | investigating/INFERENCE                    | 追加調査→spec-analysis UNKNOWN→question-analysis |
| 実装共通構造・画面構造                       | INSPECTIONとして記録、仕様へ昇格しない     | test-target-inspection/ui-target-analysis        |
| 有効仕様競合、scope/例外/合否根拠が不明      | investigating、UNKNOWN/Qの正規参照         | spec-analysis→question-analysis                  |
| 仕様UNKNOWNでない任意確認                    | investigating/deferred、`unknown_ref=null` | question-analysis                                |
| リスク、環境、手順、再利用可能な観察         | 未検証FindingをKNOWLEDGE化しない           | test-analysis/qa-knowledge/project-context       |

仕様UNKNOWNは既存`question_ids.py`の検証を経た正規UNKNOWNだけを参照します。candidate IDをUNKNOWNへ偽装しません。既存質問/回答を使う前に質問artifact、scope、revision、承認状態、現行Authorityを照合します。回答受領だけでは解決しません。

質問・知識・defectの保存APIと並行作成一意性は現在のmainで一律に提供されていません。各ownerの実経路でlookup→重複確認→既存承認→native CAS/unique guarantee→独立readbackが確認できない操作は`blocked_unverifiable`です。read-only調査・ownerへの準備情報・他の独立候補は継続します。`question_ids.py`は同一質問artifact内の採番であり別artifact間のsemantic uniquenessではありません。defectのduplicate checkも外部並行create一意性を証明しません。

## 5. State、freshness、merge/split

candidateは7状態`uninvestigated|investigating|resolved|rejected|deferred|superseded|blocked`を持ち、鮮度・scan completenessは別軸です。resolvedへは必要範囲の有効なowner readbackが必要です。rejectedはowner根拠とauthority basis、supersededは保存済み後継・根拠保持・base revision一致後です。blocked/deferred/resolved/rejectedから条件変化・一時障害解消・合否必須化により安全に再開します。

currentnessは直接参照ref/revision/content hash/effective authority fingerprint/環境・build・権限・Entity条件を比較します。source本文不変でもAuthority失効/置換、情報取得可能化、新規反例/独立支持、過去回答scope・承認変化は再評価理由です。未評価反例を質問省略・PASS/FAILへ使いません。

mergeでは継承先を先に保存/readbackし、継承元のbase content hash/revision、継承先の有効性・根拠保持、後継循環を同一保存条件で確認します。競合時は元を有効なまま保持しblockします。splitでは各根拠・resolution/回答を各target scopeへ再評価し、履歴はrelated refsで追跡します。

## 6. Runと副作用順序

開始時snapshot/予定集合/予定payload/hash/related preconditions/write metadataを持つ`in_progress` runを保存し、readbackします。永続的handoff前にsemantic handoff key、target scope、intent、reason、pendingを保存します。外部副作用後に結果保存が中断したら、ownerをreadして同一意図の既存反映を探します。既存確認が不可能で冪等性が保証されないcreateは再実行しません。

保存境界の`operation_id`はworkflow operation identityとは別です。本文・expected revision・関連候補前提・認可またはwrite metadataが変わる新判断は元操作の結果を確認した後で新IDを使います。完全同一再送だけ同じIDを使います。Skillはhost、保存方式、branch、認証方式を選択しません。保存境界のない環境では正式保存と完了をblockedにし、独立したread-only調査を続けます。

## 7. 機密情報

raw credentials、個人情報、ユーザー回答全文、最小限のQAに不要なlocator、Git commit metadata内の秘密を記録しません。秘密を含むraw値のhashだけを保存して安全と扱いません。regex検査は全PII保証ではありません。曖昧な箇所は省き、取得確認や人の判断を依頼します。
