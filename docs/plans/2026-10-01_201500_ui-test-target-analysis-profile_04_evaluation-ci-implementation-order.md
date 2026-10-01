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

最低限3 caseを追加し、合計5 caseを想定します。実装前に既存rubricとcase数集計を確認し、既存命名規則へ合わせます。

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

semantic rubricへcriteria追加が必要な場合も、既存SPEC criteriaと重複させずprofile固有のものだけ追加します。

## 3. question-analysis semantic eval

既存caseを確認し、必要なら1〜2 case追加します。

重点:

- 元UNK IDを保持する
- 暫定回答を勝手にDECISIONへしない
- 正式回答後にspec-analysisへ戻す
- 回答済み論点を再質問しない
- current unknownとresolved historyを混同しない

question-analysisの既存分類ロジックを変更しないため、trigger boundaryを広げる目的のcase追加は原則不要です。

## 4. qa-workflow routing eval

既存routing fixtureへprofile routing caseを追加します。

最低5 case:

1. UI仕様理解packageのみ
2. UI仕様理解package + 質問あり
3. 回答反映後のresume
4. current live UI観測要求
5. 仕様理解完了後もtest design不要

expected start / resume Skillを明示し、全Skill固定順実行へ回帰しないことを確認します。

## 5. trigger eval

spec-analysis SKILL.md frontmatter descriptionを変更しない、または既存意味範囲内の表現補強だけで済む場合はtrigger datasetを無理に追加しません。

descriptionを変更してselection boundaryへ影響する場合だけ、positive / negative queryを追加します。

特に次の誤選択を防ぎます。

- 「実画面を見てcurrent UIを記録」→ test-target-inspection
- 「テスト重点を決めたい」→ test-analysis
- 「テストケースを作りたい」→ test-case-design
- 「仕様理解packageを作りたい」→ spec-analysis

## 6. 機械判定可能な整合

production runtimeは初回実装では追加しません。

まずSkill契約 + assets + semantic evalで実装します。

ただしrepository testまたはdeterministic evalで低コストに確認できる次は対象です。

- asset内の必須template filenameが存在する
- README / MANIFEST templateが同じversion placeholder contractを持つ
- current unknown templateとresolved historyを同じ表として定義していない
- spec-analysisのResource参照先が存在する
- qa-workflow routing caseのSkill名が正規19 Skillに含まれる
- EVALS.mdのcase数が実datasetと一致する

実Agent出力の任意packageをmerge / parseする汎用validatorは初回では作りません。

## 7. 将来のvalidator追加条件

実運用で次の失敗が繰り返し発生した場合だけ、spec-analysis local helperまたはdeterministic validatorを追加検討します。

- version不一致
- READMEのunknown件数不一致
- MANIFESTへのfile登録漏れ
- resolved UNKがcurrent unknownに残る
- current file参照切れ

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

semantic case数、routing fixture数等の現在値が変わる場合:

- EVALS.md
- README.md
- docs/PROJECT_CONTEXT.md
- repository testのexpected count

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
- package構造を作れる
- question-analysisが必要論点だけ扱う
- test-analysisへ自動進行しない
- outputがprofileの品質ゲートを満たす

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

- SKILL.mdに条件付きResource導線
- references/ui-test-target-analysis.md
- package assets

この時点ではquestion-analysis / qa-workflowは変更しません。

### Step 2: spec-analysis eval

- semantic cases
- rubric必要差分
- dataset count同期
- Agent Skills structure validation

profile単体が成立してからworkflowへ接続します。

### Step 3: question-analysis連携

- stable UNKNOWN参照
- 回答正規化後のspec-analysis resume
- output templateの関連UNKNOWN ID
- semantic regression

### Step 4: qa-workflow routing

- profile request routing
- answer resume
- live target観測との分岐
- routing fixture

### Step 5: cross-repository validation

- 全19 Skill構造
- trigger
- deterministic
- semantic
- routing
- docs current count
- git diff --check

### Step 6: 実Agent smoke

- UI target package scenario
- question-analysis回答反映からspec-analysis package更新までのscenario

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
- UNKNOWN answer lifecycleが定義済み
- repo implementation status分離が定義済み
- qa-workflow routing / resumeが評価で確認済み
- test-target-inspectionへのcurrent UI分岐が維持される
- existing CI / evalが全PASS
- 実Agent smokeがPASS
- current repository counts / docsが同期
- 対象外のruntime / generic document frameworkを追加していない
