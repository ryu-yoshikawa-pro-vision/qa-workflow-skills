# 静的テスト・探索／QA Knowledge・継続改善の実装契約

## 対象と既存責務

本書は、Plan上の工程名だけが存在して実際の実施経路がない状態を防ぐため、**製品要件・設計・コードの静的テスト**、**正式TCを前提としない直接開始**、**QA活動評価から次回計画への反映**を定義する。

- `test-architecture-design`：品質特性・テストレベル／タイプと、レビュー／静的解析の方式・適用基準・必要環境。
- `test-management`：実施対象の母集団・優先度・担当・期限・開始／終了基準、改善採用後の計画改版。
- 既存`adversarial-review`：Agentが行う**意味的な製品要求・設計・コードレビュー**にも対象を拡張する。既存QA成果物・Playwright E2E testwareのレビューは維持する。
- 新設予定`testware-execution`：案件で採用・許可された**静的解析ツール／lint等の実ツール**を実行し、ツール固有のraw出力・実行条件・対象revision・取得完全性を保持する。静的解析を動的実行・TC判定と混同しない。
- `defect-management`：静的レビューFindingから正式Issueへの承認・引継ぎと追跡。
- `test-reporting`：レビュー対象／実結果の読取集約と未実施・未取得・誤検出の区別。
- `test-evaluation`：改善の根拠、効果測定、未測定・改善不成立と再評価。
- 既存`exploratory-testing`：Charter起点の探索・owner不明hypothesis調査。既存`qa-knowledge`：知識のtriage・lookup・revalidation／history。

新設の中央static-testing Skill・改善専用Skill・グローバル台帳は作らない。責務の拡張に伴う既存Skillの入力・trigger・非trigger・validator・回帰を実装・検証する。

## 1. 静的テストの単独開始と実施契約

### 入口と必要入力

ユーザーから製品要件書、設計書、コードrevision、静的解析結果、特定の変更差分に対するレビューを依頼された場合は、**正式TR／TCの作成を必要条件とせず**、要求された静的テストから直接開始する。

- 対象source／文書refとrevision、取得範囲・完全性、適用する仕様Authority／規則・採用基準
- 依頼するレビュー対象・観点、採用するレビュー技法／静的解析ツールとversion、対象ファイル／構成
- 必要な承認と外部I/O・アクセス権限、許可された副作用、結果の保存先
- 元のFindingや修正差分がある場合は、その参照と修正確認対象

### Agentの意味的レビュー

`adversarial-review`は対象をQA成果物に限定せず、要求・設計・コードの意味的整合、不明点・矛盾・欠落・追跡性をチェックする。ただし、仕様やコードの正本を変更しない。期待挙動は`spec-analysis`等の有効な根拠を使用し、レビュー対象そのものをAuthorityへ昇格しない。

対象の種類・検出ルール、根拠位置、期待される基準、実際の不整合、影響・重大度、反証、判定不能、重複・誤検出候補をレビュー結果へ保存する。根拠が欠ける部分のみ停止し、取得済み範囲のレビュー結果を保持する。

### ツールによる静的解析

`testware-execution`は、許可されたツール／scriptを実行する前にコマンド連鎖・対象scope・ファイル変更や外部I/Oの副作用を確認する。入力に必要な実装済みtestwareやTCが存在しなくても、明示された静的解析ツールの実行が成立する。

- raw tool出力・終了コード・対象commit／ファイル、rule／config・tool version、列挙・実行の完全性、未解析範囲を保持する。
- exit 0、問題0件、ツール未実施、取得失敗、途中で停止した解析を区別する。
- 結果の意味的な誤検出判定が必要なら`adversarial-review`または適切な仕様ownerへ渡し、ツールのraw結果を書き換えない。
- 実行条件・対象revisionが変われば必要範囲を再解析する。環境・ルール変更後の結果を旧基準の結果と無条件に比較しない。

### Finding・修正確認・統合報告

1. Findingには、対象sourceの場所・revision、review／tool／rule ref、観測された事実・仕様または規則との相違、重大度、根拠、誤検出の判定・未確認、担当・次の行動を保持する。正式TC IDを必須にしない。
2. 欠陥候補となるFindingだけを`defect-management`へ渡す。承認・認可や外部Issue状態を偽らない。原因未確定・仕様不明は必要なownerに差し戻す。
3. 修正通知後は**変更後のsource revision**を固定し、元のreview／tool ownerで同じ適用基準による再確認を行う。元のFindingを消さず結果の関連を保持する。
4. `test-management`は予定レビュー／解析対象の全列挙・対象版を保持し、`test-reporting`は実際の取得件数と母集団の差を読取専用で照合する。部分レビュー、ツール失敗、未実施を「Finding 0件・完了」にしない。
5. 製品実装・正式仕様の変更はQAのレビューSkillの権限に含めない。必要な修正は担当者へ引き継ぐ。

### 必須受入

- 要求書の矛盾、設計書の条件欠落、コード上の規則違反、採用した静的解析ツールのraw結果を**各々単独起点**から処理する。
- 未取得source、ルール不明、誤検出候補、tool起動失敗、修正後の差分再確認を検証する。
- Findingの候補と正式Issue、レビュー対象の予定数と実取得数、raw出力と解釈結果が混同されないことを確認する。

## 2. 探索的テスト・QA Knowledgeの直接開始

既存の`exploratory-testing`と`qa-knowledge`の責務・正本を維持し、[継続workflow Plan](./2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)の直接入口と受入ケースに組み込む。

- **Charter起点の探索**：`exploratory-testing`の`exploration`へ、目的・scope・side effect・cleanup・Charterを渡す。正式TC／TR／E2E testwareを作成することを開始条件にしない。
- **owner不明の症状調査**：既存ownerが対応できない`symptom／hypothesis／unresolved Finding`だけ`investigation`へ渡す。既知TCの実行やE2E既存原因分析を探索Skillへ移さない。
- **知識の参照・再検証**：`qa-knowledge`の`lookup／history／revalidation`は直接開始できる。必要なsource／環境／revisionが確認できたentryだけ現在の判断へ返す。
- **改版の影響**：source revision変更によって影響を受けるentryのみ再検証する。Repository全体のHEAD変更だけで全entryを失効させず、古いentryを有効として再利用しない。
- **再利用**：既存の分析SkillがcurrentなQA Knowledgeを入力として読むだけなら、毎回`qa-knowledge`をgatewayにしない。新たなKnowledge正本も作らない。

必須受入は、TCなし探索Session、原因owner不明の調査、既知E2E失敗を誤ってinvestigationへroutingしない負例、Knowledge直接lookup、部分revalidation、古いentryの拒否とする。

### QA Knowledgeのidentity・適用範囲・現在性

`qa-knowledge`の保存・読取・検索・再検証は、既存`skills/qa-knowledge/references/data-contract.md`にある`entry_ref`、`identity`、`kind`、`scope_refs`、`applicability`、`currentness_dependencies`を使用する。別のKnowledge正本、索引、共通schemaは作らない。

**変更対象**：`skills/qa-knowledge/scripts/knowledge_runtime.py`の`validate_entry()`、`create_entry()`、`read_entry()`、`lookup()`と既存更新・再検証の呼出し元、`skills/qa-knowledge/evals/deterministic/validator.py`、関連するdata contract・fixture・runtimeテスト。

1. **識別と適用対象の一致**：`identity.kind`と直下の`kind`、`identity.scope_refs`と直下の`scope_refs`は値・配列の内容および順序が一致していることを決定論的に検証する。`identity`は有効な`kind`と空でない`scope_refs`を含む構造でなければならない。識別に含む配列の順序を無断で正規化しない。
2. **保存時と参照時の同一保証**：新規作成、更新、置換、再検証、検索の各経路で同じ識別不変条件を適用する。`entry_ref`が正しいだけで有効と判定しない。既存entryが不整合なら、直下の値を採用して別scopeへ流用したり、`identity`を自動修正して別IDへ再採番したりせず、そのentryを拒否して正本ownerへ戻す。既存の履歴・native CAS条件を維持する。
3. **保存revisionの受渡し**：`read_entry()`は`entry`本体と`entry_revision`を別の戻り値として返す。呼出し元は保存revisionを付けた検証用入力を`lookup()`へ渡す。保存されたMarkdown本文へ`entry_revision`を追記しない。実際に取得した保存revision以外を合成しない。
4. **検索の順序**：rootの列挙完全性、entryの読取可否と適用範囲の判定に必要な構造・identity整合を確認した後、依頼された`scope_refs`／`kind`／environment／versionに該当するentryに対して内容・currentness・依存sourceの検証を行う。**適用範囲が確実に異なるentryの依存source取得不能は、該当する有効entryの利用を止めない**。
5. **適用可能性を判断できないentry**：破損・識別不一致・適用範囲未解決のentryがある場合、関連性不明のまま無関係と決めつけず、検索の完全性を`incomplete`とする。root列挙の失敗・途中打切り・同一ref重複も全件取得済み扱いしない。適用対象entry自身の依存source不明・無効・staleは、有効なKnowledgeとして返さず、既存の除外・未解決情報を残す。
6. **部分再検証**：変更された依存sourceを持つ関連entryだけ再検証する。別scopeのentryをすべて再検証することや、単なるrepo HEAD更新で全Knowledgeを失効させることを必須にしない。各検索時に実際のsource revisionを再確認し、古い検索結果を無条件に再使用しない。
7. **状態の分離**：検索対象の有効entry集合、履歴として除外したentry、不完全で返せない検索を区別する。対象外entryの依存取得失敗は必要なら診断情報へ記録するが、対象検索の`status`を不当に`incomplete`にしない。

**必須受入**：

- `identity.scope_refs=A`なのに直下の`scope_refs=B`、または`identity.kind`と`kind`が異なるentryを投入し、作成・更新・検索で拒否する。正しい`entry_ref`でも受理しない。
- Aの有効entryとBの依存revision取得不能entryを同一rootへ置く。Aのlookupは有効entryを返し、Bの依存不明を理由に停止しない。
- scope不明・identity破損・重複ref・root途中打切りでは安全側の`incomplete`となり、検索全件完全を主張しない。
- `create → read → lookup → 更新／部分revalidation → lookup`を別Agentセッション間で行い、`read_entry().entry_revision`を受渡してcurrentnessとCASを照合する。
- 既存QA Knowledgeのentry ID・保存形式・状態、履歴・replacement、claim／CAS、直接lookup・history・部分revalidationと、決定論的validatorの回帰を行う。

## 3. QA活動評価から計画・設計・実施への戻り

`test-evaluation`が提案した改善を、知識化しただけで実施済みとしない。改善案の採否・実施と効果測定は異なる成果物ownerで追跡する。

1. `test-evaluation`は、問題の根拠・対象QA活動・指標・測定条件・原因候補、改善案・担当・期限・必要承認・検証方法を保持する。
2. 改善案の採用権限は案件の承認ポリシーに従う。承認を得て採用する場合、改善が変更する正式正本へ引継ぐ。**計画／予算／資源／実行順序は`test-management`、方式・環境・品質特性は`test-architecture-design`、正式TC等の設計は元設計owner**が更新する。
3. 変更を受けたownerは、引継いだ改善参照・旧／新revision・採用／承認状態・実施状況・影響する下流を保持する。単に計画を提出しただけでは実施済みにしない。実変更がない場合は理由と未実施状態を残す。
4. 実施後は`test-evaluation`が、同等の条件の次回QA活動から測定値を取得して効果を判定する。測定不能、比較条件不一致、未実施、効果なし、悪化、改善を区別する。必要なら別の改版・差戻しを行う。
5. 汎用的に再利用できる知識候補のみ`qa-knowledge`へ渡す。**Knowledgeへの登録は計画改版・承認・実施・効果測定の代用ではない**。
6. 元実績・正式テスト結果・承認のraw情報を`test-evaluation`が書き換えない。

### 必須受入

- 原因分析の遅延や実行準備の非効率が評価で見つかり、計画・手順が採用／承認→改版→実施→次回比較測定される。
- 未承認、承認済み未実施、実施済み未測定、比較不能、改善なし・悪化を、実際の改善達成件数へ誤算入しない。
- 計画改版から関連アーキテクチャ・Risk・実行準備だけへ影響が伝播し、無関係なcurrent成果物を維持する。

## 完了条件

1. Agentによる意味的レビューとツールによる静的解析を、正式TC不要の独立した入口から実施でき、Finding・誤検出・修正確認・統合報告に接続できる。
2. 探索・症状調査・Knowledgeのlookup／revalidationは単独開始でき、既存のCharter・entry lifecycleと安全条件を維持する。QA Knowledgeのidentityと適用対象は一致し、無関係なentryの依存不明だけで有効な検索を停止しない。読取revisionを伴う別セッション再開と部分revalidationを実証する。
3. 改善案の採用・計画等の正本改版・実施・効果測定が各ownerで追跡でき、Knowledgeや報告だけで完了扱いしない。
4. 公式シラバスへの参照は該当活動・成果物の根拠として扱い、Skill分割・データ形式やAgent起動方法をシラバスが指定しているとは主張しない。
