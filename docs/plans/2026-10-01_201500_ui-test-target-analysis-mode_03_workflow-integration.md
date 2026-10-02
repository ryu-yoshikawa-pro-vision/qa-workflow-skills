# UIテスト対象分析モード: workflow integration

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

この文書はquestion-analysisとqa-workflowの統合契約を正本とします。

## 1. question-analysis変更

### 1.1 目的

mode packageのUNKNOWNを、回答反映のたびに再質問・再採番せず継続管理できるようにします。

既存のブロッカー / 要確認 / 仮定可能 / 提案・任意分類は変更しません。

### 1.2 SKILL.md

必要最小限の追加:

- 入力がspec-analysisのUNK-xxxを持つ場合、そのstable IDを保持する
- 回答済み論点を新しい質問IDだけで別論点化しない
- 回答反映で複数仕様fileが変わる場合でも、Authority正規化後はspec-analysisへ戻す
- versioned UI target packageの差分反映責務はspec-analysisであり、question-analysis自身がpackageを編集する責務を持たない

### 1.3 references/guidance.md

「回答の正規化」を次で補強します。

- 元UNKNOWN IDを保持する
- 暫定回答と正式回答を区別する
- 暫定回答が後で正式DECISIONへ変わっても同じUNKNOWN lineageを使う
- 「回答が不明」は回答履歴として残してもUNKNOWNは解消しない
- 正式回答で解消したUNKNOWNはcurrent unknownから除外し、spec-analysisでcurrent Authorityのstable IDを`解消先ID`へ記録する
- 解消済み事項を、根拠がcurrentな間は再質問しない
- 後続更新で`解消先ID`のAuthorityが置換・失効しても別current Authorityが同じ論点を解消している場合は、同じUNK lineageの`解消先ID`を新しいcurrent Authorityへ更新する
- 解消根拠がなくなった場合、同一論点か新しい競合かをLLMが判断する。同一論点なら同じUNK IDを`現在有効か=Yes`へ戻して再openし、新しい競合なら旧UNKNOWNをresolved historyとして維持してnew UNKを作る
- UNKNOWNのopen / resolved / reopenに伴う`現在有効か`、`解消先ID`、CHANGELOG eventの形式整合はdeterministic helperが検証し、同一論点かどうかの意味判断は行わない

### 1.4 assets/output-template.md

既存Q-xxxを廃止しません。

次の列を追加します。

- 関連UNKNOWN ID

さらに、同じquestion-analysis成果物へmachine-readableな使用済みID台帳を追加します。

```markdown
## 質問ID履歴

| ID |
| --- |
```

`不明点 / 質問一覧` はcurrent未解決質問だけを持ち、templateはheader-onlyにして `Q-001` の例示rowを実データとして残しません。`質問ID履歴` はcurrent / resolvedを問わず、その成果物系列で一度でも使用したQ IDを重複なし昇順で保持します。新規Qのsemantic identity / reuse判断はLLM、newと決めた後の番号決定と履歴union生成は `question_ids.py` が担当します。

spec-analysis由来の論点ならUNK-xxxを記録し、質問単位のQ-xxxと仕様UNKNOWNを追跡できるようにします。mode packageからquestion-analysisへ進む場合は `ui_target_package.py inspect` の `current_unknown_ids[] / resolved_unknown_ids[]` を正規handoffとし、Agentが09から集合を手作業で再構築しません。

値は空欄または1件以上の `UNK-xxx` とし、複数参照は `<br>` 区切りに固定します。QとUNKが意味的に対応するかはLLMが判断し、`unknown_links.py` は形式・存在・duplicateだけを検証します。新しいUNKNOWN registryは作りません。

### 1.5 Skill-local deterministic helper

新規に次を追加します。

- `skills/question-analysis/scripts/unknown_links.py`
- `skills/question-analysis/scripts/question_ids.py`

stdin / stdout JSON、operation名、failure、size limit、sort順等の正確なCLI契約は `_06_package-schema-and-helper-contracts.md` を正本とします。

`unknown_links.py` は次を決定論的に検証します。

- `関連UNKNOWN ID` の非空値が `UNK-xxx` 形式であること
- current known UNKNOWN集合に参照先が存在すること
- 同一Q内で同じUNKを重複参照していないこと
- current / resolved集合が与えられた場合、resolved-only UNKをcurrent questionへ関連付けていないこと

`question_ids.py` は次だけを担当します。

- `不明点 / 質問一覧` と `質問ID履歴` の `Q-xxx` をparseする
- current質問ID / 使用済み履歴IDのduplicate / malformedを拒否する
- LLMがnew questionと判断した後、current + historyの既知最大番号+1を返す
- previous artifactとcandidate current artifactから、previous current Q + previous履歴 + current Qのunionをcanonical `質問ID履歴` tableとして生成する
- `Q-999` 使用済みなら既存3桁ID契約を勝手に拡張せず `id_space_exhausted` を返す

この2 helperはQとUNKの意味的対応、質問文、回答後の正規化先、reuse / newの意味判断を行いません。

### 1.6 deterministic eval

既存 `skills/question-analysis/evals/deterministic/validator.py` も同じ外部契約を独立に評価します。

- fixtureに `known_unknown_ids` がある場合、参照UNKNOWNがその集合に含まれること
- fixtureに `expected_related_unknowns` がある場合、Q IDごとの関連UNKNOWN集合が完全一致すること
- spec-analysis由来でない質問は関連UNKNOWN ID空欄を許可する
- 既存Q-xxx、分類、再開Skill、runtime identity等の契約は変更しない

eval validatorはproduction helperをimportしてexpectedを作りません。既存QUESTION output fixtureの少なくとも1件へUNKNOWN mappingと`質問ID履歴`を追加し、repository unit testで未知UNK / 誤mappingのfalse-pass regressionを追加します。さらに `Q-001解消 → current質問0件 → 新規質問` で `Q-002` が割り当てられ、Q-001を再利用しない回帰を追加します。deterministic output case数を増やす必要はありません。

## 2. qa-workflow変更

### 2.1 routing

次の要求をspec-analysisのUI target modeへroutingします。

- テスト設計前の対象理解を、後続工程で再利用する継続成果物として整理したい
- 複数資料からPAGE / MODAL / STATE、業務ルール、不明点を統合したい
- 既存UI target packageを更新したい
- 不明点回答をpackageへ反映したい
- 「テスト対象分析」「対象理解を固める」等が主目的で、テスト観点 / ケースへまだ進まない

単なる「Markdownで出して」という形式要求だけではmodeへrouteしません。単発要約やAuthority解消だけなら通常spec-analysisを使います。

基本経路:

spec-analysis(UI target mode)
→ unresolvedがあればquestion-analysis
→ 回答正規化
→ spec-analysis(UI target mode)差分更新
→ ユーザー要求が仕様理解までなら完了
→ テスト分析も要求されている場合だけtest-analysisへ進む

### 2.2 gated mode

ユーザーが「1手順ずつ」「理解を確認してから」「ファイル出力前に確認」等を指定した場合、既存gated modeを使います。

mode固有の新しいmodeは作りません。

### 2.3 test-target-inspection routing

次の場合だけtest-target-inspectionへ進めます。

- currentな実画面の表示名 / 到達可否が必要
- 仕様資料だけでは現在UI状態を判断できない
- userが実画面のcurrent観測を要求
- repository情報ではなく実対象の観測が必要

repositoryを読むだけの調査をtest-target-inspectionと呼びません。

### 2.4 repository調査

repository事実が必要で、AIエージェントがrepositoryを利用できる場合は補助入力として収集できます。

ただし:

- repo factはAuthorityではない
- spec-analysis packageの08へ分離
- 実装差分はquestion-analysisへ不要な仕様質問として戻さない
- Authority上の期待挙動が明確なら差分として記録する

特定のrepository接続方式、connector、tool名はSkill契約へ固定しません。

### 2.5 routing fixture

PR #14後の61 routing fixtureをbaselineとして、次の2ファイルを必ず同時に更新します。

- `skills/qa-workflow/evals/deterministic/routing_cases.json`
- `skills/qa-workflow/evals/deterministic/routing_candidate_outputs.json`

expected routingからcandidate outputを自動生成せず、既存契約どおり独立fixtureとして保持します。

次の8 caseを追加します。

1. 「テスト設計前に仕様理解を複数Markdownへ整理」→ spec-analysis UIテスト対象分析モード
2. 「既存仕様理解packageへ不明点回答を反映」→ question-analysis解消後spec-analysis mode resume
3. 「current実画面を見て対象資料を更新」→ test-target-inspection
4. 「仕様書とrepoを比較して期待仕様を整理」→ spec-analysis mode。repo差分をAuthority化しない
5. 「仕様理解だけで止めたい」→ test-analysisへ自動進行しない
6. 「保存済みFigma / screenshotをUI/UX観点で評価」→ usability-evaluation
7. 「live browserで使いやすさ / focus / responsiveを検査」→ usability-inspection
8. 「WCAG 2.x / level指定でformal適合性評価」→ wcag-conformance-evaluation

routing fixtureはPR #14後の61件から8件追加して69件になる想定です。実装開始時にStep 0で現在値を再確認し、追加数が変わらなければEVALS.md / docs/PROJECT_CONTEXT.md / routing件数を保持するrepository contractを69へ同期します。READMEにrouting件数を持つ場合のみ同様に更新します。

### 2.6 DEC / ASMの正本ownerとdefault Project Context採番

question-analysisが回答を正式 `DECISION` または承認済み `ASM` へ正規化する場合、ID ownerは案件で実際に指定されている決定事項 / 仮定の正本です。UI target package側では採番しません。

Project ContextのSection 12 / 13が正本ownerであるdefault経路では、新規 `skills/qa-workflow/scripts/project_context_ids.py` を使います。

- `## 12. 確定事項（決定事項の正本一覧）` → `DEC-xxx`
- `## 13. 仮定（仮定の正本一覧）` → `ASM-xxx`

LLMは回答の意味、DECISION / ASMの区別、既存identityのreuse / new、決定内容、関係、影響範囲、ASM承認可否を判断します。Project Contextがownerの場合、newと判断した後の番号だけhelperが既知最大番号+1で返します。

案件で別の決定事項 / 仮定の正本一覧が明示されている場合はそのownerを維持し、Project Contextへ複製・再採番しません。owner側にdeterministic ID allocatorがあればそれを使い、ownerがIDを確定できない状態ではLLMが番号を推測せず正本登録をblockedとして扱います。任意schema向けgeneric allocatorは追加しません。

`skills/qa-workflow/assets/project-context-template.md` を正本ownerとして使う場合、Section 12 / 13はheader-onlyへ変更し、現在の `DEC-001` / `ASM-001` 例示rowを実データとして残しません。

helperはProject Contextを書き換えず、正本tableをparseして次IDを返すだけです。exact CLI契約は `_06_package-schema-and-helper-contracts.md` を正本とします。

### 2.7 downstream machine handoff

UI target modeから後続テスト設計へ進む場合、spec-analysis成果物のMachine Entity / normalized inputをAgentがMarkdownから再構築しません。

`ui_target_package.py build-machine-evidence` が返す次を正規handoffとして使用します。

- spec-analysis canonical `normalized_skill_input`
- Authority Machine Entities
- current Acceptance Criterion Machine Entities
- expected entity identities

qa-workflow / coverage-analysisはshared runtime contractからAuthority + current ACのexpected Entityを内部導出します。

ユーザー要求が仕様理解packageまでならspec-analysisの完了条件で終了し、test-analysis / test-requirement-designを起動しません。この場合、AC→TR / Disposition closureはpackage単体の完了条件ではありません。

test-requirement-designへ到達した場合は `requirement-structure-v2` を使用し、`build-machine-evidence` が返したcurrent ACの `ac_id / authority_refs[]` を `acceptance_criteria[]` としてそのまま渡します。各TRの意味対応だけをLLMが `acceptance_refs[]` として判断し、AC / AuthorityのID集合・Entity存在・dependency展開・closure・freshnessはdeterministic runtimeが検証します。AgentがACからAuthority参照を再構築しません。

このhandoffの追加はrouting caseを増やしません。既存workflowの選択結果に対するmachine data受け渡し契約です。
## 3. Agent Skillsとしての利用前提

今回のmodeは既存Skillと同じAgent Skills構造で提供します。

- entry pointはskills/spec-analysis/SKILL.md
- 詳細規則はreferences/ui-test-target-analysis.md
- package templateはassets/ui-test-target-analysis/
- qa-workflowは必要なSkillへroutingする
- question-analysisは回答正規化とresume情報を返し、新規Qの番号はquestion_ids.pyで決定する
- qa-workflowはProject Context Section 12 / 13が実際の正本ownerの場合だけproject_context_ids.pyでnew DEC / ASMの番号を決定する。別ownerが明示されている場合はその正本IDを維持する

AIエージェントは利用環境で提供される通常のSkill読み込み機構に従います。

今回の実装では次を追加しません。

- 特定AI製品向けbootstrap
- GitHub connector固有手順
- remote Skill loader
- 新しいSkill-to-Skill API
- 全22 Skillを一括読み込みするruntime

## 4. PR #14成果物のAuthority扱い

usability-evaluation finding、usability-inspection observation / measurement、wcag-conformance-evaluation result / report / EARLは、そのままSPEC / DECISION / approved ASMへ昇格しません。

- 既存Authorityとの一致 / 差分を対象理解packageへ補助evidenceとして記録できる
- 仕様変更が必要ならquestion-analysis / stakeholder decisionへ送る
- project contextでformal WCAG requirement自体がAuthorityとして明示されている場合はrequirementをAuthorityとして扱えるが、評価結果そのものは仕様へ自動変換しない

## 5. README更新

READMEへ、UIテスト対象分析modeがspec-analysisの条件付きmodeであることと、詳細契約の参照先を簡潔に追記します。通常spec-analysisを置換しないことも明記します。

特定AI製品の利用手順は追加しません。

## 6. 変更しないもの

- qa-workflowのPR #14後22 Skill前提
- skill-to-skill API不存在の説明
- question-analysisの分類4種
- DECISION / ASMの意味判断と、案件で明示された決定事項 / 仮定の正本owner
- test-target-inspectionのlive target currentness契約
- runtime / artifact graph
- qa-knowledge lifecycle
- Regression / Exploration routing
- E2E Skill群

## 7. 完了条件

- mode requestがspec-analysisへrouteされる
- 不明点回答後に同じUNKNOWN lineageでspec-analysisへ戻り、question-analysisの関連UNKNOWN IDはSkill-local helperと独立deterministic evalの双方で構造検証される
- new Q / DEC / ASMのsemantic identityはLLMが判断する。Q番号はquestion-analysis helper、Project ContextがDEC / ASM ownerの場合はqa-workflow helper、別ownerの場合はそのownerのdeterministic allocatorで番号を決定し、owner未採番時にLLM hand-numberingへfallbackしない
- 仕様理解だけの要求でtest-analysisへ勝手に進まず、AC→TR / Disposition closureをpackage単体の完了条件にしない
- current UIの対象情報観測要求だけtest-target-inspectionへ分岐する
- 保存済みUI資料のUX評価はusability-evaluation、live usability検査はusability-inspection、formal WCAG適合性評価はwcag-conformance-evaluationへ分岐する
- modeが既存Agent Skills構造でAIエージェントから利用できる
- 特定AI製品向けintegrationを追加していない
