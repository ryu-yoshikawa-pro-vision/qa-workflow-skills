# UIテスト対象分析モード: scope / responsibilities

親Plan:
2026-10-01_201500_ui-test-target-analysis-mode.md

この文書は、今回追加する「UIテスト対象分析モード」のSkill間責務境界を正本とします。LLMと決定論的処理の内部責務境界は `2026-10-01_201500_ui-test-target-analysis-mode_05_llm-deterministic-boundaries.md`、package schema / helper I/O / legacy migrationは `2026-10-01_201500_ui-test-target-analysis-mode_06_package-schema-and-helper-contracts.md`、PR #14後のSkill境界は `2026-10-01_201500_ui-test-target-analysis-mode_07_pr14-baseline-and-integration.md`、UI操作のUS / UC / Behavior / AC分解と下流追跡は `2026-10-01_201500_ui-test-target-analysis-mode_08_behavior-decomposition-and-acceptance-traceability.md`、Acceptance Criterion Machine Entity / shared runtime / test-requirement-design v2は `2026-10-01_201500_ui-test-target-analysis-mode_09_runtime-entity-and-test-requirement-contracts.md` を正本とします。

## 1. 解決する問題

現在のspec-analysisはAuthority解決、SPEC / DECISION / INFERENCE / UNKNOWN分類、業務ルール、状態・遷移、フロー、制約を扱えます。

ただし、UIテスト設計前に長期間更新する「対象理解package」として、次が固定されていません。

- PAGEと同一route内状態の区別
- MODALとbrowser標準dialogの区別
- 仕様上の期待挙動とrepository実装状況の区別
- 未解決事項のcurrent一覧と解消履歴
- 回答反映後の複数ファイル同期
- package全体のversion / changelog / manifest
- 案件固有の大規模仕様を複数ファイルへ分割する判断

この追加責務はAuthority ownerを増やさず、spec-analysis内の条件付きmodeとして実現します。

AIエージェントからの利用方法は既存のAgent Skills構造をそのまま使い、今回のための製品固有integrationやbootstrap機構は追加しません。

## 2. 責務表

| 内容 | owner | 今回の変更 |
| --- | --- | --- |
| 現在有効な仕様根拠 | spec-analysis | 既存維持 |
| SPEC / DECISION / INFERENCE / UNKNOWN分類 | spec-analysis | 既存維持 |
| UI構造の仕様上の分類 | spec-analysis | modeへ追加 |
| UI操作母集団 / User Story / Use Case / Behavior / Acceptance Criteria | spec-analysis | UI操作scopeでは必須分析としてmodeへ追加 |
| 複数Markdown仕様理解package | spec-analysis | modeへ追加 |
| mode導入前のlegacy package migration | spec-analysis | semantic mappingはLLM、current schema validationはhelper |
| canonical仕様モデル / Current Effective Authority / Authority Machine Entity | spec-analysis | 既存契約を維持し、package内の単一正本へ配置 |
| Acceptance Criterion Machine Entity | spec-analysis | current ACだけを下流handoff用Entityとして決定論生成。US / UC / Behaviorはstructured modelのまま |
| 不明点のブロック分類 | question-analysis | 既存維持 |
| 回答のSPEC / DECISION / ASM正規化 | question-analysis | 安定UNKNOWN参照を補強 |
| packageへの回答反映 | spec-analysis | question-analysisの正規化結果を入力に更新 |
| 生きた実画面のcurrent観測 | test-target-inspection | 変更なし |
| 保存済みFigma / screenshot / evidenceのUI/UX意味評価 | usability-evaluation | #14責務を維持 |
| live browserでの使いやすさ / focus / responsive / feedback検査 | usability-inspection | #14責務を維持 |
| formal WCAG-EM適合性評価 | wcag-conformance-evaluation | #14責務を維持 |
| repositoryの製品コード事実 | spec-analysisの補助入力 | Authorityへ自動昇格しない。E2E実装分析そのものが必要な場合だけe2e-test-inspectionへroutingする |
| プロダクトリスク / テスト重点 | test-analysis | 対象外 |
| Acceptance Criteria → テスト要求の追跡 / closure | test-requirement-design | test-requirement-designまで進むworkflowで`requirement-structure-v2`によりcurrent ACをTRまたはDispositionへ閉じる。仕様理解package単体の完了条件にはしない |
| テスト条件 / ケース | 各既存設計Skill | 変更なし |
| workflow開始 / 再開 / 変更伝播 | qa-workflow | mode routingのみ追加 |

## 3. PR #14 Skillとの境界

入力資料が同じでも目的でownerを分けます。

- 仕様・UI構造・状態・業務ルール・UNKNOWNを対象理解packageへ整理 → spec-analysis UIテスト対象分析モード
- 保存済みFigma / screenshot / evidenceをUI/UX観点で評価 → usability-evaluation
- live browserを操作して使いやすさ / focus / responsive / feedbackを検査 → usability-inspection
- WCAG version / levelを指定したformal適合性評価 → wcag-conformance-evaluation

#14成果物は補助evidence / observation / issue候補として参照できますが、それ自体をSPEC / DECISION / approved ASMへ自動昇格しません。product requirement変更が必要ならquestion-analysis / stakeholder decisionを経由します。

## 4. modeを使う条件

modeの選択は「Markdownを要求されたか」ではなく、成果物の目的で判断します。

### modeを使う

次のいずれかに該当する場合:

- テスト設計前の対象理解を、後続工程や別セッションでも再利用する継続成果物として残す
- 仕様書、Figma、Q&A、repository等の複数資料を統合し、画面・状態・業務ルール・不明点を追跡可能に管理する
- PAGE / STATE / VIEW / MODAL等のUI構造を正規化し、今後のテスト分析の入力にする
- 既存のUIテスト対象分析packageを更新 / version upする
- 「テスト対象分析」「対象理解を固める」等、テスト設計前の対象モデル作成が要求の中心である
- テスト観点 / ケースへ進む前に対象理解だけを確定して止める

### 通常spec-analysisを使う

次の場合は既存 `assets/output-template.md` を使い、modeを強制しません。

- 一回限りの仕様要約
- Authority競合の解消だけが目的
- 単一表で十分な小規模仕様整理
- SPEC / DECISION / INFERENCE / UNKNOWN分類だけで要求を満たせる

mode選択を「Markdown」「複数ファイル」等の単語一致だけで決めません。

## 5. UI操作scopeの必須分析

分析対象機能scopeごとにUI操作有無を判断します。UI操作ありはUS → UC → Behavior → ACをrequired、UI操作なしはnot-applicable、UI操作有無自体が未確定ならblocked + UNKNOWNです。資料不足をnot-applicableへ置き換えません。ユーザー操作を起点としない自動更新・session timeout・非同期表示更新等はUS / UCを無理に作らず、通常のstate / rule / notification等として残します。

正常 / 準正常 / 例外はUse Case仕様の完全性確認軸であり、テスト技法ではありません。詳細は `_08_behavior-decomposition-and-acceptance-traceability.md` を正本とします。

## 6. canonical仕様モデルと構造化ビュー

UIテスト対象分析packageでも、既存spec-analysisのcanonical contractを維持します。

- canonical正本: `09_authority_and_traceability.md`
- 既存 `assets/output-template.md` と同じ意味契約で、SRC / 分析項目 / Current Effective Authority / Machine Entityを保持する
- 他のpackage fileはcanonical item IDを参照する構造化ビューであり、SPEC / DECISION / INFERENCE / UNKNOWNの別正本を作らない
- 業務ルール、UI構造、入力制約等を人間向けに再配置しても、期待挙動のAuthorityは09へ戻れる
- Current Effective AuthorityからAuthority Machine Entityを生成する既存 `authority_entities.py` 契約を維持する
- current ACだけを `acceptance_criterion` Machine Entityへ変換し、US / UC / Behaviorはglobal Entity typeへしない
- package固有のversion / manifestはAuthority Machine Entityのidentityやfingerprintを置換しない

## 7. UI構造の正規分類

modeでは次の意味を固定します。

### PAGE

URL / route / page pathを単位とする画面。

同一path上の条件表示やstepだけで別PAGEを作りません。

pathが資料から確定できない場合は推測せずPATH-TBD等の明示的な未確定値を使えます。

### STATE

同一PAGE上で、契約状態、データ有無、権限、利用上限等により成立する状態。

複数条件が同時成立できる場合は、排他的なSTATE列挙へ無理に押し込まず、契約軸、データ軸、制限軸等の独立状態軸として整理します。

### VIEW / STEP

同一route内で操作や処理成功により切り替わる表示段階。

例:
- 入力 → 確認
- 発行フォーム → 発行完了

routeが同一であることをAuthorityまたは確認済み事実から判断できる場合はPAGEとは分離します。routeが不明な場合に、操作フローだけを根拠としてsame-route VIEW / STEPへ推測統合しません。資料上別画面として扱われているがpathが未確定なら `PATH-TBD` を保持し、PAGE / VIEW分類自体が後続設計へ影響する場合はUNKNOWNとして残します。

### MODAL

アプリケーションUIとして描画されるmodal / dialog。

親PAGE、起動条件、閉じ方、共有componentかを追跡できる形にします。

### BROWSER-DIALOG

beforeunload、window.confirm等のブラウザ標準UI。

MODALへ分類しません。

### PANEL / POPOVER / GLOBAL UI

global navigation、通知panel、drawer等、独立routeではない共通UI。

### EXTERNAL

Intercom、ご利用ガイド、外部サイト等。

### SHARED PAGE

共通404等、本機能専用ではないが遷移・権限制御上重要な共通画面。

## 8. 仕様と実装の分離

次を必須ルールとします。

1. 仕様資料、正式決定、承認済みASMを期待挙動のAuthorityとして扱う
2. repositoryや実画面は既存契約どおり補助証拠
3. repositoryで仕様と異なる挙動を見つけても、仕様本文を実装に合わせて書き換えない
4. 差分はimplementation status / spec-implementation gapとして分離する
5. 未実装は「仕様不明」ではなく「仕様は定義済み・実装未確認 / 未実装」と区別する
6. repositoryだけでは決められない仕様を「コード上こうなので仕様もこう」と確定しない
7. 案件コンテキストが実装をAuthorityと明示した場合だけ、既存Authority解決契約に従って扱う

## 9. 不明点の扱い

mode内の仕様UNKNOWNはspec-analysisの安定IDとしてUNK-xxxを使います。

question-analysisは既存契約どおり質問単位のQ-xxxを持ち、spec-analysis由来の論点では元のUNK-xxxとの対応を保持します。同じ論点を新しいUNKとして再採番しません。

回答後:

- Authority資料更新 → SPEC
- 正式なステークホルダー決定 → DECISION
- 暫定前提 → 承認済みASM
- 回答が不明 / 判断不能 → UNKNOWN継続

解消したUNKはcurrent unknown一覧から外しますが、回答反映済み履歴またはchangelogから追跡可能にします。

「一度回答があるが暫定だった論点」を再確認する場合も、同じUNK IDを使います。

## 10. packageとtest-target-inspectionの関係

mode packageは「仕様上どうあるべきか」を中心にします。

test-target-inspection成果物は「現在の実対象で何を観測したか」です。

modeからcurrent実対象確認が必要になった場合:

1. qa-workflowがtest-target-inspectionへrouting
2. 観測結果を観測事実として取得
3. 観測結果をspec-analysisへ補助入力として戻す
4. 仕様と一致 / 不一致 / 仕様未定義を区別
5. 観測事実だけでSPEC / DECISIONへ昇格しない

## 11. 進行モード

既存qa-workflowのcontinuous / gatedをそのまま使います。

今回のように「まず理解を説明して確認後にファイル化」「1手順ずつ合意する」と明示された場合はgatedで扱います。

gatedの場合:

- spec-analysis package draftまたは理解説明を提示
- ユーザー承認前にtest-analysisへ進まない
- question-analysis回答待ちでもブロッカーでない範囲はpackage更新可能
- 次工程はユーザー承認後のみ

## 12. LLMと決定論的処理

意味判断はLLMに残します。具体的には、SPEC / DECISION / INFERENCE / UNKNOWN、PAGE / VIEW等の分類、semantic identity、Authority競合、scopeのUI操作有無、条件付き必須file trigger該当性、案件固有extension fileの必要性、repository差分の意味判断をscriptへ固定しません。

定型処理は `05_llm-deterministic-boundaries.md` に従い、ID形式・参照存在・scope applicability対応・条件付き必須file整合・version整合・current UNKNOWN件数・MANIFEST / SHA-256・AC Machine Entity / normalized machine input・evaluation projection等をhelper / validatorへ移します。

helperの出力はLLMの再確認候補や構造エラーを示すための補助であり、仕様意味を新しく確定する根拠にはしません。

## 13. 対象外となる誤った統合

次は実装しません。

- test-target-inspectionをspec-analysisへ吸収する
- repository実装をデフォルトAuthorityにする
- modeを全spec-analysis requestで強制する
- test-analysisのリスク評価をmodeへ複製する
- test-condition-designのテスト技法をmodeへ先回りする
- coverage-analysisを使わずmode独自にテストカバレッジを判定する
- 任意形式文書を統合する汎用document engineを作る
