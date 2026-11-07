# 開発変更とQA成果物の継続的な追跡・抽出網羅率強化 Plan

## 対象ブランチと目的

- 実装ブランチ：`feat/development-qa-traceability`
- 調査基準：`main` commit `329cd8ad75ecde9d21c2e60f791214ca27fa2602`（2026-11-07確認）
- この文書は実装Plan。Plan作成時点でコード、Skill、CI、テストは変更しない。
- 実装着手時には作業ブランチのHEADと`main`、関連する未マージPRの変更を確認し、競合・前提変更を解消する。目的・範囲・完了条件を独自に縮小しない。

**目的**：開発で実装・変更される製品全体の機能と振る舞いを継続的に抽出・構造化し、現在有効な仕様とQA成果物の対応を維持する。初回の全体分析、PR更新、マージ後、リリース前の各時点で、機能抽出漏れ、仕様未反映、テスト不足、陳腐化した成果物を検出し、必要なQA活動へ接続する。

「開発側の確認済み情報源から見つかった全候補を追跡できること」と「製品全体の全機能を確実に発見できたこと」は区別する。情報源が未確認・不完全な場合は抽出網羅率を製品全体の保証として提示しない。

## 合意済みの要求

1. 抽出対象はUI、API、バッチ、外部連携、権限、データ処理を含む製品機能全体。単なる画面一覧へ縮小しない。
2. 開発情報源はIssue、仕様書、設計資料、コード、PR差分、既存テスト、必要な実対象観測。利用可能な各情報源の確認範囲・revision・未確認範囲を記録する。
3. 初回全体分析に加え、PR更新・マージ後・リリース前に継続確認する。前回成果物を再利用し、変更影響のある範囲を再確認する。
4. 未分類の開発差分はCI失敗。分類済みの仕様・テスト不足は根拠とプロダクトリスクに応じて判定する。失敗・警告・ブロック中を混同しない。
5. Skillの肥大化を避け、独立した責務は分割する。ただし機能構造、仕様、テスト設計、workflow状態に重複する正本を作らない。

## 現状と既存契約

### 確認した実装

| 現行owner / ファイル | 再利用する契約 | 残る不足 |
| --- | --- | --- |
| `skills/spec-analysis/SKILL.md`、`references/ui-test-target-analysis.md` | 有効な仕様根拠、SPEC / DECISION / INFERENCE / UNKNOWN、UI target package | UI以外を含む製品全体の機能母集団・抽出網羅率の正本がない |
| `skills/spec-analysis/assets/ui-test-target-analysis/00_scope_and_context.md` | `SCOPE`の対象範囲とready / blocked、`UIOP → US → UC → Behavior → AC` | SCOPEには親Scope列がなく、製品機能全体の階層とは一致しない |
| `skills/spec-analysis/assets/ui-test-target-analysis/01_ui_structure_and_navigation.md` | 画面・状態等のUI構造の親子参照 | 機能階層の代替にはできない |
| `skills/spec-analysis/assets/ui-test-target-analysis/08_repository_implementation_status.md` | 確認済みRepositoryのrevision・実装事実 | 開発情報源全件の発見・差分母集団の完了判定ではない |
| `skills/spec-analysis/scripts/ui_target_package.py` | UI packageのID、参照検証、UNKNOWN、snapshot、Machine Entity、原子的更新 | 追加責務を同ファイルへ集中させない（調査時約218 KB） |
| `skills/test-analysis/scripts/change_impact.py` | 既知変更からの最短影響経路 | ノード型はAuthority / Risk / TR / TCN / CI / TCで、開発差分・製品機能を直接扱わない |
| `skills/coverage-analysis/scripts/traceability.py` | 仕様・Risk・TR・TCN・CI・TCの追跡性と閉鎖性 | 抽出前の開発機能候補、情報源確認の完全性は対象外 |
| `skills/qa-workflow/SKILL.md`、`scripts/artifact_graph.py`、`scripts/workflow_runtime.py` | routing、局所blocked、freshness、状態・revision・CAS、previous baseline | 開発差分を起点とした機能抽出・再分析の入口を追加する |
| `skills/test-target-inspection/SKILL.md` | 実対象の観測事実、条件、鮮度、安全・cleanup | 観測事実を仕様Authorityに自動昇格しない |
| `skills/regression-testing/`、既存E2E Skill | baseline、対象選定、実装・実行結果 | 機能差分から関連TC / E2E / Regressionの再評価に接続する |

現行UI target packageは`ui-target-v1`、既存Machine Entityは`entity-state-v2`。Scope ownership、部分再実行、stale / deleted / legacy、Machine Runtime証拠、前回成果物からの復元と移行経路は既存契約を尊重する。`qa-workflow`と`qa-knowledge`の保存先・並行更新・現在性の契約を別実装で置換しない。UI target packageは案件側の成果物であり、このSkillリポジトリに製品固有データを書き込まない。

既存テストの参照先：`tests/skills/runtime/test_ui_target_package.py`、`test_test_analysis_change_impact.py`、`test_coverage_analysis_traceability.py`、`test_traceability_runtime.py`、`test_qa_workflow_runtime.py`、`test_migration_preflight.py`、`tests/skills/evals/{deterministic,semantic}/`。

CIの正本：`.github/workflows/validate-skills.yml`、`deterministic-output-evals.yml`、`semantic-output-evals.yml`、`code-quality.yml`。これらは主として本Skill repositoryを検証し、利用先製品の開発イベントを自動収集する仕組みではない。

参照：`PLANS.md`、`.agents/skills/feature-plan/SKILL.md`、`docs/plans/2026-10-01_201500_ui-test-target-analysis-mode.md`、`docs/plans/2026-09-22_123900_qa-artifact-graph-harness.md`。

## 責務分担と変更範囲

### 新規の機能分析Skill

`skills/feature-analysis/`を追加し、製品機能の発見、機能階層、開発情報源との対応、候補の分類、抽出網羅率、機能単位の変更判定を担当する。これは仕様Authorityの判断やTC生成を担当しない。

- `SKILL.md`：利用契機、入力、責務境界、停止条件。
- `references/guidance.md`：情報源調査、機能同定、分解、抽出漏れ検査、変更・削除、分類の意味判断。
- `references/data-contract.md`：情報源snapshot、開発差分、機能一覧、階層、参照、分類、網羅率の機械可読契約。
- `assets/output-template.md`：人間が確認できる機能一覧、抽出・未確認・対応関係、判定結果。
- `scripts/`：既存Python 3.11 runtime契約に従い、構造・参照・revision・網羅率・差分・状態遷移を決定論的に検証する。意味判断はAgentと当該Skillが担当し、推測を構造検証で正当化しない。
- `evals/`：trigger、deterministic、semanticの正本データとvalidator。共通評価runtimeを再実装しない。

Skillの新設は、機能の母集団と階層がUI対象分析や仕様根拠とは異なる正本だからである。情報源ごと、画面/APIごと、指標ごとのSkillを増やさない。内部Pythonモジュールは入力正規化、候補照合、階層・参照検証、網羅率、履歴・永続化の責務で分割し、巨大な単一スクリプトを作らない。

### 既存Skillとの接続

| owner | 変更する責務 |
| --- | --- |
| `feature-analysis` | 開発側の機能候補と機能構造の正本、抽出網羅率、開発変更の分類 |
| `spec-analysis` | 新機能IDから現在有効なAuthority / UNKNOWN / 既存SCOPE・UI構造・ACへの明示的対応。仕様の正本は継続して本Skill |
| `test-analysis` | 変更機能と関連Authority・Riskを入力に既存影響分析を利用。リスク採点・深度判断は現行owner |
| `test-requirement-design`以下 | 既存のAuthority / AC→TR→TCN→CI→TCを維持。機能IDを理由に重複TRやTCを強制生成しない |
| `coverage-analysis` | 新Skillで確認済みの機能・仕様対応結果を受け、機能→仕様→テスト設計のギャップを分析。抽出母集団は再計算しない |
| `qa-workflow` | 初回・PR更新・マージ後・リリース前から開始し、blocked / stale / 再開 / 局所再検証をroutingする |
| `regression-testing` / E2E | 変更影響の確定した既存TC / 自動テストとリリース対象revisionの実行状態を再評価する |

既存`ui-target-v1`のSCOPEは**仕様分析の作業範囲**として維持し、新しい機能IDと同一視しない。初期接続は`feature-analysis`側の明示的な`(package ref, Scope ID)`参照で行い、既存package schemaを無断で変更しない。複数機能↔複数SCOPE、機能↔UI構造・API・ジョブ等の多対多を許すが、機能階層の親は一つとし、共有・横断的な依存は別の参照で表す。既存データの無根拠な機能ID再採番は禁止する。

## データ・計算契約

### 1. 開発情報源の棚卸しと取得範囲

製品案件ごとに取得可能な情報源と今回の確認対象を記録する。少なくとも次を区別する。

- 情報源：Issue / 要件、仕様書、設計資料、Gitリポジトリ（コード・設定・schema・API定義・既存テスト）、PRの全変更差分、必要な実対象観測。
- 各情報源の識別子、アクセス権、取得方法、確認対象（リポジトリ、branch、path、文書群、対象環境・ロール等）、revision / commit SHA / 文書版 / 取得時点、証拠参照。
- 列挙結果と完全性：一覧を最後まで列挙できたか、API pagination、未取得のpath / 文書、解析不能な形式・言語・生成物、到達できない観測対象を記録する。
- 確認対象として選定しなかった情報源・除外領域には理由と承認主体を残す。取得できなかったものを「対象外」に変更しない。
- ソースが利用可能でも、製品全体の機能を網羅する一次資料があるとは限らない。情報源の完全取得と製品の機能発見の完全性を別に示す。

外部サービス固有のAPI取得・認証は当該サービスの既存接続手段を利用し、解析ロジックは正規化された証拠入力から独立させる。接続手段がない情報源は検証済みの手動提供・輸入経路を設け、未確認のまま成功にしない。Gitの全体snapshot・PRの差分は決定論的に列挙し、変更ファイル数を機能件数と見なさない。

### 2. 開発差分と機能候補

- 初回は対象revisionのソースと文書から機能候補を抽出。継続時は前回基準と今回のrevisionから追加・変更・削除・rename / moveを識別する。実装上のノイズ（formatのみ等）は証拠付きで機能影響なしと分類する。
- 変更差分には一意な識別子、根拠source、旧/新revision、対象path / symbol / document locator、変更種類、機能影響の判定、判定理由、関連機能ID、未解決事項を記録する。複数ファイルの一機能を重複計上しない。
- 機能候補は重複・統合と分割を意味判断で処理し、元候補と対応先を保存する。推論だけの候補を正式仕様へ昇格しない。
- 変更を解釈できない場合は`未分類`または`未解決`とし、「影響なし」「対象外」へ推測変換しない。削除された機能に残る参照・テストも影響対象とする。
- feature IDは案件内で安定し、名称変更・移動は同じ意味なら維持。分割・統合・廃止は旧IDとの対応、revision、証拠を記録する。循環、孤立した親、ID衝突、無根拠な再利用をrejectする。

### 3. 機能構造

- 「製品→領域→機能→サブ機能」の階層は必要な粒度まで分解する。UI、API、バッチ、外部連携、権限、データ処理を同じ製品機能モデルに置く。
- 機能と実装要素の参照を分離し、同一機能に複数UI・API・ジョブ等が属してよい。APIや非同期処理が独立した検証対象の場合は意味に従って機能としても分解する。
- 子機能の確認・未分析範囲、各機能の存在を裏付けるsource、現行revision、仕様参照、QA成果物参照、影響・状態を保持する。
- 共通処理の再利用は機能階層の複数親にせず、参照・依存として保持。複数製品repositoryを含む場合も製品・repositoryの境界を明示する。
- 非機能要件や横断的な制約は勝手に機能へ変換せず、適用機能への関連付けと既存Authority / Riskで扱う。権限や監査等の振る舞いが機能として識別できる場合はその機能を管理する。

### 4. 指標・完了性

計算結果には数値だけでなく、母集団の証拠、対象revision、分母・分子の対象ID、対象外、未解決、情報源の取得完了状態を含める。以下は別指標とし、片方の100%を他方の完了の代用にしない。

| 指標 | 計算・判定 |
| --- | --- |
| 開発差分分類率 | 確認できた開発差分のうち、理由付きで機能影響あり / 影響なし / 対象外に分類した件数 ÷ 全確認差分。未分類・未解決は分子に含めない |
| 機能抽出網羅率 | 確認済みの対象機能候補のうち、安定した機能IDに対応し証拠付きで抽出した件数 ÷ 確認済みの対象機能候補総数。重複候補の正規化・除外理由を記録する |
| 仕様対応率 | 有効な仕様根拠へ対応付けられた対象機能 ÷ 対象機能。UNKNOWN、実装観測のみ、未確認を分子へ含めない。仕様が不要と判断された場合は別の理由付き扱いとする |
| テスト設計対応率 | 対象機能に関連する有効なAuthority / ACの下流が、現行のTR・TCN・CI・TCまたは正当なDispositionに閉じている割合。実際の適切性は`coverage-analysis`で意味確認する |
| テスト実行状況 | 対象revision・環境のrequired execution routeに対する実行済み / 未実行 / blockedと結果内訳。実行とPASSを混同しない |

分母0、情報源の列挙未完了、候補同定不能、未解決差分、対象revision不一致、必要な上流成果物不足には、数値とは別に`complete=false` / `blocked` / `unknown`相当の判定を付ける。分母0を機械的に100%にしない。現在確認できた情報源に対する100%を「製品全体の全機能を確認」と報告しない。

### 5. 変更影響・鮮度・保存

- `開発差分→機能→Authority / AC→Risk / TR→TCN→CI→TC→実装 / 実行`の明示関係を既存のEntity・変更影響・freshnessに接続する。機能とAuthorityの意味対応はAgent / ownerが判定し、近接pathや同じScopeだけで自動推定しない。
- 変更機能の下流のみ`要再検証`。依存が不明な範囲は「影響なし」ではなく`unknown`とし、確認完了まで該当判定を止める。無関係なcurrent成果物は再利用する。
- 候補・機能・参照の履歴を保持し、削除後に同じIDを別の意味へ再利用しない。差分比較は前回と今回の明示的snapshot、artifact revision、source SHAを用いる。
- 保存先は対象プロジェクトが管理するartifact root。製品固有の仕様・コード断片・証跡を`qa-workflow-skills` repositoryに保存しない。既存`qa-workflow`の保存・CAS・revision / snapshot契約を再利用し、共有mutable rootを単純なread→比較→無条件writeで更新しない。
- 履歴・currentnessは「いつ分析したか」だけでなく「どの開発revisionと情報源で分析したか」で判断する。過去の結果と最新結果は書き換えずに比較可能にする。
- 既存`ui-target-v1` packageや下流成果物との連携では、新機能IDとのcrosswalkを明示して移行。対応が一意でない旧成果物を推測移行せずblocked。移行検証前の旧成果物を削除しない。

## 開発イベントとCIの契約

共通解析・検証はAgentからの手動実行とCIからの実行の両方を提供する。GitHub依存を新Skillの意味モデルへ埋め込まず、Git / GitHubの入力収集と正規化された検証を分ける。

| 時点 | 処理と判定 |
| --- | --- |
| 初回全体分析 | 対象製品の明示baselineを全列挙し、情報源確認・機能抽出・階層・対応を確定。未確認領域があれば全体完了にしない |
| PR作成・更新 | base/headを固定して変更ファイル・Issue / 文書等の関連差分を取得し、全差分を分類。前回PR更新からの差分と、新しいbaseとの差分の両方を取りこぼさない |
| PR CI | 情報源列挙の失敗、未分類差分、欠落した分析証拠、旧revision結果の使い回し、参照不整合はfail。分類済み仕様 / テストのギャップは承認済みルールとRisk・理由でfail / warning / blockedを判定 |
| マージ後 | 実際のmerge commit / target branchを新基準として検証。PR headの解析結果だけでマージ済みrevisionのcurrentを証明しない |
| リリース前 | リリース対象のcommit / build、必要な環境・ロール・feature flagと成果物の基準revisionを照合。機能・仕様・テスト・実行状態と未解決リスクをまとめて判定する |

CIが扱う「変更差分の全件」は、イベントから決まるbase / headと確認対象に対して列挙できた全差分を意味する。外部Issueや設計資料の変更が観測できないときは、それを監視済みと偽らず、対応するsourceの未確認と再確認条件を示す。PR間に変更された外部資料もsource revision比較で検出する。

製品repository向けGitHub Actions接続、ローカルCLI、入力 / 出力schema、権限、導入手順を実装対象とする。既存CIを利用して必要な検証を実行し、再利用可能なworkflowまたは同等の手順で対象repositoryのPR・merge・releaseイベントに接続する。外部repositoryのCIに検証を追加しただけで、製品固有の実行環境に接続済みと誤認しない。

CI判定方針：

1. 開発差分が未分類、source discoveryが必要範囲で未完了、必須証拠がない、snapshot / revisionが古い場合はfail / blocked。テストが足りないかどうかの判断以前にQA評価可能性を確保する。
2. 分類済みの仕様未対応、テスト未対応、未実行は、そのままPASSにしない。対象機能・Authority・Risk・必要なテストレベル、正当なDisposition、明示された承認者・根拠に従い判定する。判定規則・承認主体が未設定なら自動で安全側を採用し、無根拠なwarningへの格下げを許さない。
3. CI上でリスクを自動採点し直さない。Riskは`test-analysis`、仕様は`spec-analysis`、テスト網羅は`coverage-analysis`、実行事実はexecution ownerを正本とする。
4. informational reportと合否の機械可読結果を同時に出す。GitHub UIのcheck結果やコメントだけを成果物の正本にしない。
5. 変更のないPRでもsource範囲・revisionの妥当性を確認し、空差分を「全製品網羅100%」として扱わない。

## セキュリティ・運用

- 機能抽出用のコードやPR本文、Issue本文、設計資料、実対象観測は外部から来る信頼できない入力。Skill/Agentの指示や権限として解釈せず、データとして解析する。LLMが作った候補・判定は根拠とreviewを経ず確定しない。
- PR CIは最小権限の読み取りを基本に、fork等の未信頼コードに秘密情報・書込み権限を渡さない。`pull_request_target`で未信頼headを実行しない。外部資料の取得権限がない場合はblockし、権限昇格で迂回しない。
- secret、認証token、個人情報、顧客データ、未公開設計資料の本文、危険なログをrepoや公開CI artifactへ無条件保存しない。証跡は参照・revision・必要最小限の抜粋とし、保持期間・保存先・アクセス権は案件の既存方針を使う。
- Git解析では外部コマンド、パス、symlink、巨大入力、binary、特殊文字、履歴不足、API pagination / rate limit、タイムアウト / ネットワーク障害を扱う。証拠不足を空の成功結果へ正規化しない。
- 実対象観測は`test-target-inspection`の許可origin、権限、副作用・cleanup契約を使い、必要な場合だけ実行。観測結果を仕様の期待結果にしない。
- PRと同時進行workflowでは同じcurrent成果物の競合をCASで扱う。PRイベントの再配信、順不同、重複実行、失敗後の再開、旧revisionの遅延完了をテストする。
- 自動でコード修正・テスト生成のcommit・merge・release・権限変更は行わない。CIは分析・検証・報告を行う。

## 実装手順

### 1. baseline・責務境界の再確認

- `main`と当branchの最新差分、関連PR、既存UI target / Machine Entity / migration / QA workflow contract、既存tests / CIを再読込する。
- 情報源発見・機能母集団・機能IDの唯一のownerを確定し、`SCOPE`との意味差・reference形式・schemaの互換性を明文化する。
- 対象製品repositoryへ導入する際のartifact rootとGitHub event / source access条件をProject Contextから解決する。未設定値を暗黙既定にしない。

### 2. 情報源・開発差分の入力契約

- `feature-analysis`のsource snapshot、discovery completeness、開発差分、機能候補、証拠refを定義。
- 初回のGit tree / repoファイル列挙とbase/head差分取得、Issue・仕様・設計・テスト・観測の入力正規化、重複判定、取得失敗の表現を実装。
- 手動提供とCI入力の両方で同じ契約を検証。対象製品の全体source discovery不足をfail-closedにする。

### 3. 機能構造・網羅率

- 新Skillと人間可読artifactを作成。安定ID、parent、cross-reference、分割・統合・廃止、情報源との対応を実装。
- deterministic helperでschema、参照、循環、重複、revision、候補と機能の閉鎖、分母・分子を検証。意味上の分解粒度や対象外の正当性はsemantic品質確認へ渡す。
- 情報源未確認・分母0・unknown・対象外・重複・機能なしの差分・partial discoveryの表示と完了判定を個別に検証する。

### 4. 既存仕様・設計成果物への接続と移行

- `feature-analysis`→`spec-analysis`のAuthority / UNKNOWN / SCOPE crosswalk、`test-analysis`の変更影響、`coverage-analysis`の上流機能対応を追加する。
- 既存`entity-state-v2` / Runtime evidence / scope ownership / currentnessを尊重し、必要な型・参照を既存ownerのcontractに沿って追加。未知ノードを既存runtimeが無条件受け入れる実装にしない。
- 既存UI target package、通常spec-analysis、legacy成果物、既存TR/TCN/CI/TC、partial rerunの互換性を保ち、migration前後のID・依存・履歴・再開位置を検証する。関連が不明な旧artifactはblockedにする。

### 5. 継続workflow・CI接続

- `qa-workflow`で初回 / PR更新 / マージ後 / リリース前の開始・再利用・再開を実装。旧revisionと最新revisionの区別、局所stale、影響なしの証拠、未分類時のfailを確認。
- 製品repository向けの呼び出し方法、GitHub Actions連携、必要なsource input / artifact root / permissionを明示し、GitHub eventの重複・競合・fork・secretへの安全対策を実装。
- reportには開発差分全件、機能抽出、仕様対応、テスト設計、実行状況、未確認source、Riskと判定根拠を別々に表示する。

### 6. 評価・文書・検証

- 新Skillのtrigger / deterministic / semantic caseを追加し、既存Skill側のroutingと回帰caseも更新する。
- README、EVALS、Project Context関連の導入説明、既存workflow、CI利用手順、migration / recovery手順を更新する。
- 以下の独立検証を実施して結果を記録する。成功した一部テストで他の失敗・未実行を代替しない。

## 検証

### 決定論的テスト

1. 初回全体source列挙：複数repo、複数形式、API / バッチ / UI / 権限 / データ処理、文書のみ、コードのみ、既存テストのみの候補。
2. PR差分：追加・変更・削除・rename、同一機能の複数ファイル、共通処理、重複候補、formatのみ、外部Issue・文書変更、途中pagination失敗、未知形式。
3. データ整合：安定ID、複数機能と一つのSCOPE、親循環、子の孤立、分割・統合・廃止、削除済み機能への参照、欠落したAuthority / SCOPE。
4. 指標：分母0、母集団の再定義、未確認source、未分類差分、正当な対象外、UNKNOWN、partial discovery、数値100%と`complete=false`の両立。
5. 鮮度・保存：無関係な変更の再利用、影響するAuthority / AC / TR以下のstale、旧revisionの拒否、並行更新・CAS conflict、部分再開、前回revision不在、原子的保存とfailure recovery。
6. セキュリティ：パストラバーサル、symlink、巨大入力、secret/PIIの出力防止、信用できないPR本文内の命令、fork権限、外部取得不能時のfail-closed。

### 意味品質・統合テスト

- 初回全体分析で機能階層と実装要素の分離が適切か、機能の過分割・過統合・未抽出・重複、根拠不足を独立に評価する。
- 実装で観測した挙動を正式仕様に昇格させないこと、UIなし機能が消えないこと、権限・例外・非同期・外部連携が対応する仕様とテストに接続すること。
- PR差分→機能→Authority / AC→TR→TCN→CI→TC→関連実行結果の代表ケースと、関連情報が足りずblockedになるケース。
- 初回、PR更新、マージ後、リリース前、並行PR、旧baselineからの移行を含むAgent workflow E2E評価。構造テストだけでsemantic品質をPASSとしない。
- CI integrationは実際のテスト用製品repository / fixtureでPRイベント・merge・release対象を検証し、GitHub Actions上の安全性と失敗・警告判定を確認する。外部環境にアクセス不能な試験は未検証として区別する。

### 既存コマンド・CI

- `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`
- `python -m unittest discover -s tests/skills/evals/deterministic -v`
- `python -m unittest discover -s scripts/skills/evals/deterministic/tests -v`
- `python scripts/skills/evals/semantic/validate.py`
- `python -m unittest discover -s tests/skills/evals/semantic -v`
- `python -m unittest discover -s scripts/skills/evals/semantic/tests -v`
- `python -m unittest discover -s tests/skills/evals/trigger -v`
- 公式`skills-ref validate skills/<name>`（全current Skill）、`python scripts/format_tracked.py check`、`python .github/check_patch_whitespace.py`、`git diff --check`。
- `Validate Agent Skills`、`Validate Deterministic Output Evals`、`Validate Semantic Output Evals`、`Code Quality`のGitHub Actionsを個別に確認。既存ハーネス・他workflowへの回帰も対象とする。
- 外部sourceとlive対象に依存する受入は、対象revision・権限・テスト環境・基準source一覧が揃って初めて判定する。

## 完了条件

以下を**すべて**満たしたときだけ実装完了とする。

1. 対象製品全体の機能抽出を扱う新Skillが存在し、UI以外の機能も同じ契約で構造化・差分更新できる。情報源の確認範囲、未確認領域、機能候補、機能IDと証拠を独立して追跡できる。
2. 初回全体分析、PR更新、マージ後、リリース前の各経路が動き、source revisionと成果物revisionを照合できる。認証・対象環境不足があれば未検証・blockedにする。
3. 開発差分の未分類や必要なsource列挙失敗はCIで失敗し、分類済み仕様・テストの不足はRisk・根拠・承認条件を踏まえてfail / warning / blockedに分類される。
4. 開発差分分類率、機能抽出網羅率、仕様対応率、テスト設計対応率、実行状況を混同せず算出する。情報源の確認が不完全でも100%と全体完了を誤認させない。
5. 既存Authority / UNKNOWN / SCOPE / AC、TR / TCN / CI / TC、Regression・E2E実行結果を参照でき、仕様の二重正本・機能の重複正本・不要なGraphを作らない。
6. 新規・変更・削除・分割・統合の機能IDと履歴を維持し、影響するQA成果物だけを再検証対象とする。影響不明を「影響なし」にしない。
7. 同じ製品の並行PR・失敗再試行・rebase・merge・releaseに対して、currentness、CAS、過去結果保護、秘密情報保護、実対象操作の安全契約が満たされる。
8. 既存UI target package、通常spec-analysis、legacy、現行QA workflowsの互換性 / migration / rollback判定と回帰テストが成立する。
9. Skill / runtime / CI / 評価データ / README・利用手順・運用文書を更新し、記載した独立検証および実製品相当の統合受入がPASSする。未検証・SKIP・失敗は成功扱いしない。

## リスク・実装時の確認事項

- **完全性の限界**：コード・資料から発見できない機能の存在は機械的に証明できない。確認した情報源と分析対象境界、未知領域を表示し、誤った完全性主張を防ぐ。
- **候補の粒度**：ファイル、コード関数、画面、業務機能は一対一ではない。機能同定・重複解消・分割・統合は意味判断を要する。数だけ合わせる処理は禁止。
- **既存schemaとの整合**：`ui-target-v1`はUI分析に特化している。機能階層をSCOPEやUI構造に直接流し込むと既存の振る舞い・readiness・migrationが壊れる可能性がある。明示参照と互換性を先に確認する。
- **外部連携と権限**：接続先のIssue / 設計資料の種類やAPI契約は案件ごとに異なる。情報源の列挙・取得不能を明示する共通入力を必須にし、資格情報を必要とする個別providerを無断追加しない。
- **CI導入先**：このrepositoryのCIは製品repoのCIとは別。製品repositoryへの導入・権限・artifact保存・イベントの検証が完了しない限り、開発連動完了と報告しない。
- **実装の肥大化**：新Skillには機能抽出・機能構造・母集団管理を持たせ、仕様根拠、リスク採点、test coverage、execution、workflow orchestrationを移植しない。既存の大きな`ui_target_package.py`を今回のために全体書換えしないが、新たな接続に必要な局所変更・モジュール分離と回帰テストは省略しない。
