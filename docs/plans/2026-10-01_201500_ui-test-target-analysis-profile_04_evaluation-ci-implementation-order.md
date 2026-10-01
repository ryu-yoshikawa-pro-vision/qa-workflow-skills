# UIテスト対象分析プロファイル: evaluation / CI / implementation order

親Plan:
2026-10-01_201500_ui-test-target-analysis-profile.md

この文書は評価、CI、実装順序、完了条件を正本とします。

## 1. 評価方針

新しい評価frameworkは作りません。

既存の4層を維持します。

1. Agent Skills仕様 / repository structure validation
2. trigger selection validation
3. deterministic output / routing validation
4. semantic evaluation

今回の中心は意味分析なので、semantic evalを主とし、機械判定できるものだけ既存deterministic / repository testへ追加します。

## 2. spec-analysis semantic eval

現在spec-analysisは2 semantic caseです。

3 caseを追加し、spec-analysisは現在2件から5件へ増やします。case IDは既存命名規則に合わせて `SPEC-SEM-003` ～ `SPEC-SEM-005` を使用します。

### case A: 複数資料からUI target packageを構成

入力:
- 画面設計
- business rule
- Q&A decision
- repository補助情報
- 一部矛盾

期待:
- UI target profileを選ぶ
- SPEC / DECISION / INFERENCE / UNKNOWNを区別
- PAGEをpath単位で整理
- same-route viewをPAGEへしない
- repository差分を実装状況へ分離
- test condition / caseへ進まない

### case B: repository実装が仕様と違う

期待:
- 高Authority仕様を実装に合わせて変更しない
- spec-implementation gapとして分離
- 実装をAuthorityへ自動昇格しない
- 「不具合」と断定する必要がない場合は差分として扱う

### case C: versioned package更新

入力:
- v03 package
- 既存UNK
- 正式回答
- 新しい資料差分

期待:
- v04完全版
- 同じUNK lineage
- 解消済みをcurrent unknownから除外
- README / current unknown / changelog / manifestの意味整合
- 差分だけを最終成果物にしない

semantic rubricへはprofile固有の次の観点だけを追加し、既存SPEC criteriaと重複させません。

- canonical modelと構造化ビューの追跡性
- UI構造分類の妥当性
- implementation status分離
- versioned package更新の整合

### 複数Markdown packageのevaluation projection

既存 `scripts/skills/evals/semantic/run.py` は1つの `--output` fileだけを受けるため、semantic runner自体はdirectory対応へ変更しません。

評価時だけ、packageを次の決定論的projectionへ変換します。

1. package rootの `MANIFEST.md` に列挙されたcurrent fileだけを対象にする
2. path traversal / package root外参照を拒否する
3. MANIFESTのfile順をevaluation順として固定する
4. 各fileの前に `<!-- FILE: <relative-path> -->` markerを付ける
5. UTF-8 textをそのまま連結し、内容の要約・変換・正規化を行わない
6. 生成した1 Markdownを既存semantic runnerの `--output` へ渡す

このprojectionは評価専用で、production packageやAuthorityを変更しません。

実装は `scripts/skills/evals/semantic/package_projection.py` の小さいeval-only helperとして追加し、MANIFEST外file混入、root外path、重複file、missing file、順序をrepository unit testで検証します。汎用document merge frameworkにはしません。

## 3. question-analysis semantic eval

1 caseを追加し、question-analysisは現在2件から3件へ増やします。正式回答 / 暫定回答とUNKNOWN lineageを同時に扱うcaseを1件だけ追加します。

重点:

- 元UNK IDを保持する
- 暫定回答を勝手にDECISIONへしない
- 正式回答後にspec-analysisへ戻す
- 回答済み論点を再質問しない
- current unknownとresolved historyを混同しない

question-analysisの既存分類ロジックを変更しないため、trigger datasetは変更しません。関連UNKNOWN IDの形式・既知参照・fixture mappingはsemanticではなく既存deterministic validatorで検証します。

## 4. qa-workflow routing eval

既存routing fixtureへprofile routing caseを追加します。

5 caseを追加し、routing fixtureは現在61件から66件へ増やします。各caseは `routing_cases.json` と `routing_candidate_outputs.json` の双方へ独立に追加します。

対象:

1. UI仕様理解packageのみ
2. UI仕様理解package + 質問あり
3. 回答反映後のresume
4. current live UI観測要求
5. 仕様理解完了後もtest design不要

expected start / resume Skillを明示し、全Skill固定順実行へ回帰しないことを確認します。

## 5. trigger eval

今回のprofile選択はspec-analysis内部の出力profile選択であり、Skill間trigger境界を変更しません。現在のspec-analysis trigger datasetには、複数資料統合・テスト分析前の仕様整理・repository/Figma/Q&A統合のpositive queryが既にあるため、frontmatter descriptionとtrigger datasetは原則変更しません。

実装時にfrontmatter descriptionを変更する必要が生じた場合のみ、変更理由を明示してpositive / negative boundaryを再評価します。

特に次の誤選択を防ぎます。

- 「実画面を見てcurrent UIを記録」→ test-target-inspection
- 「テスト重点を決めたい」→ test-analysis
- 「テストケースを作りたい」→ test-case-design
- 「テスト設計前の対象理解を継続成果物として作りたい」→ spec-analysis

## 6. 機械判定可能な整合

production runtimeは初回実装では追加しません。

まずSkill契約 + assets + semantic evalで実装します。

ただしrepository testまたはdeterministic evalで低コストに確認できる次は対象です。

- required core assetがすべて存在し、optional assetをrequiredとして強制していない
- `09_authority_and_traceability.md` が既存spec-analysis canonical table / Machine Entity契約を保持する
- README / MANIFEST templateが同じversion placeholder contractを持つ
- current unknown templateとresolved historyを同じ表として定義していない
- question-analysisの関連UNKNOWN IDがUNK形式・既知参照・fixture期待mappingを満たす
- semantic package projectionがMANIFEST順だけを使用し、package root外を読まない
- spec-analysisのResource参照先が存在する
- qa-workflow routing caseのSkill名が正規19 Skillに含まれる
- EVALS.mdのcase数が実datasetと一致する

実Agent出力の任意packageを意味解析する汎用validatorは初回では作りません。追加するpackage projection helperはsemantic eval入力を1ファイル化するだけで、Markdown意味解析・merge判断・仕様修正を行いません。

## 7. 将来のvalidator追加条件

実運用で次の失敗が繰り返し発生した場合だけ、spec-analysis local helperまたはdeterministic validatorを追加検討します。

- version不一致
- READMEのunknown件数不一致
- resolved UNKがcurrent unknownに残る
- current file参照切れ
- optional domain file間の意味重複

初回から汎用document engine、ZIP validator、Markdown AST frameworkを作りません。

## 8. CI

既存workflowを再利用します。

最低限:

- Validate Agent Skills
- Validate Semantic Output Evals
- Validate Deterministic Output Evals
- repository unit tests
- git diff --check

新しいGitHub Actions workflowは追加しません。

今回の計画どおり実装した場合の想定現在値:

- Skill数: 19のまま
- trigger query: 428のまま
- deterministic output case: 38のまま
- semantic case: 72 → 76
  - spec-analysis: 2 → 5
  - question-analysis: 2 → 3
  - その他Skill: 変更なし
- qa-workflow routing fixture: 61 → 66

Step 0でmainの現在値を再確認し、上記差分がそのまま適用可能な場合は次を同期します:

- EVALS.md
- docs/PROJECT_CONTEXT.md
- `tests/skills/evals/semantic/test_semantic_datasets.py` のSkill別件数とtotal
- routing fixtureの固定件数を検証するrepository test / 文書
- README.mdは件数またはprofile説明を実際に持つ箇所だけ更新

を実データへ同期します。

歴史文書の過去値は変更しません。

## 9. 実Agent smoke

実装完了前に少なくとも1回、実Agentクライアント相当で次を確認します。

入力:
- 複数の仕様根拠
- 1件以上の正式decision
- 1件以上のUNKNOWN
- repository補助事実
- 「テスト設計へ進まず対象理解packageまで」の要求

確認:
- spec-analysisを選択する
- profile referenceを読む
- repository事実を仕様Authority化しない
- package構造を作れ、09_authority_and_traceability.mdから既存Authority Machine Entityへ閉じられる
- question-analysisが必要論点だけ扱う
- test-analysisへ自動進行しない
- outputがprofileの品質ゲートを満たす
- MANIFEST順evaluation projectionを通して既存semantic runnerへ入力できる

AIエージェント上で、既存Agent Skillsの読み込み方法に従い `spec-analysis` → profile reference / assetsを利用して成果物を生成できることを確認します。

特定製品のtool名やconnectorを評価条件にはしません。

## 10. 実装順序

### Step 0: 現状再確認

- main headがPlan基準から動いていないか確認
- spec-analysis / question-analysis / qa-workflowのcurrent契約確認
- semantic / routing datasetの現在件数確認
- README / EVALS / PROJECT_CONTEXTの現在値確認

mainが動いていてもPlanを盲目的に適用せず、責務契約が変わっていれば差分を再評価します。

### Step 1: profile責務をspec-analysisへ追加

- SKILL.mdに目的ベースの条件付きResource導線
- references/ui-test-target-analysis.md
- required / optionalを分けたpackage assets
- 09_authority_and_traceability.mdで既存canonical spec-analysis contractを維持
- 09から既存authority_entities.pyへ入力できることを確認

この時点ではquestion-analysis / qa-workflowは変更しません。

### Step 2: spec-analysis eval

- SPEC-SEM-003～005
- profile固有rubric差分
- eval-only package_projection.pyとunit test
- projectionしたpackageを既存semantic runnerへ渡せることを確認
- semantic countをspec-analysis=5へ同期
- Agent Skills structure validation

profile単体が成立してからworkflowへ接続します。

### Step 3: question-analysis連携

- stable UNKNOWN参照
- 回答正規化後のspec-analysis resume
- output templateの関連UNKNOWN ID
- deterministic validatorのUNK形式 / known refs / expected mapping
- 既存output fixture 1件へmapping追加 + false-pass unit test
- question semantic caseを1件追加し合計3件へ

### Step 4: qa-workflow routing

- profile request routing
- answer resume
- live target観測との分岐
- routing_cases.jsonへ5件追加
- routing_candidate_outputs.jsonへ対応する独立candidate 5件追加
- routing fixture合計66件へ同期

### Step 5: cross-repository validation

- 全19 Skill構造
- trigger
- deterministic
- semantic
- routing
- docs current count
- git diff --check

### Step 6: 実Agent smoke

- UI target package scenario（canonical Authority / Machine Entityを含む）
- question-analysis回答反映からspec-analysis package更新までのscenario
- semantic evaluation projection scenario

### Step 7: final review

次を確認します。

- 新Skillを不必要に追加していない
- spec-analysis / test-target-inspection境界が壊れていない
- repository実装をAuthorityへ昇格していない
- profileなしのspec-analysisが重くなっていない
- question-analysisの分類契約を変更していない
- qa-workflowが詳細ロジックを複製していない
- 特定AI製品固有のtool / connector / bootstrapをSkill契約へ入れていない
- 実装時に参照すべき正本fileが一意に分かる

## 11. 完了条件

- 新Skill追加なし
- profile assets / referenceが存在
- normal spec-analysisとprofileの選択境界が明確
- UI構造分類が定義済み
- versioned complete package契約が定義済み
- package内にcanonical Authority / traceability正本があり、既存Machine Entity契約へ閉じる
- UNKNOWN answer lifecycleが定義済み
- repo implementation status分離が定義済み
- question-analysisのUNKNOWN lineageがsemantic + deterministic双方で確認済み
- qa-workflow routing / resumeがrouting case / independent candidateで確認済み
- multi-file packageがevaluation projection経由で既存semantic runnerにより評価可能
- test-target-inspectionへのcurrent UI分岐が維持される
- existing CI / evalが全PASS
- 実Agent smokeがPASS
- current repository counts / docsが同期
- 対象外のruntime / generic document frameworkを追加していない
