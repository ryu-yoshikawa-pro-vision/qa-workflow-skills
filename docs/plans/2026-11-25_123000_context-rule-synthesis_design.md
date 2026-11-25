# QAワークフロー 詳細設計書：横断的法則性抽出・コンテキスト補完（基本設計確定版）

本ドキュメントは、複数の機能・セッション・workflow にまたがる観察結果およびユーザー回答から**横断的な法則性（暗黙ルール・不変条件・差異条件）を帰納的に抽出し、コンテキストの隙間を継続的に補完する仕組み**の基本設計・主要データ契約を確定する設計書です。

> **設計のステータスと前提**
>
> - 基準リポジトリ：現行 `main`（`a37b15508dadd17ac0228ac896badb71d6a8f2c7`）
> - 本ドキュメントをもって基本設計レビューを完了とし、実装着手前の確認事項（信頼された host の認可入口等）と詳細タスクは次フェーズの**実装Plan**へ引き継ぎます。
>
> **2026-11-25利用者決定による改訂**：2026-11-25 利用者決定：成果物は指定ディレクトリで統一管理する。Skillに案件識別・探索・切替・保存先決定・Provider選択・ブランチ管理・認証方式選択を持たせない。必要な案件境界・root・実行条件・権限はハーネスが入力として提供し、不要な管理は移管せず削除する。SkillはQAの意味判断、成果物の意味・形式・相対配置、必要な質問・引継ぎに集中する。Helperは決定論的識別・検証・保存を担当する。ハーネスの特定製品への依存、新しい汎用管理基盤、既存案件の移行は本PRの対象外。 原設計は親Plan記載の固定commitで保持する。以下の意味要件は維持し、保存・責務・identityの変更後は詳細Plan 01〜03を実装正本として使用する。

---

## 1. 目的・対象範囲・対象外

### 1.1 目的

1. **横断的な法則性・暗黙仕様の発見**: 機能単位の仕様分析では見落としやすい、複数機能にまたがる共通ルールや「挙動の違いを生む条件」を帰納的に抽出する。
2. **コンテキストの隙間補完と継続利用**: 別の日・別機能・別 workflow で得られた観察や回答を、新しい機能の QA 開始時に横断発見・再利用できるようにする。
3. **質問前の自己解決と重複質問の削減**: 仮説が出た際にまず既存スキルで一次情報・実装・実観測を確認し、既に解決済みの事項を繰り返し質問しない。
4. **作業あたりの認知負荷軽減**: 責務を明確に分離し、1ターンに読み込むコンテキスト量と全体の処理効率を最適化する。

### 1.2 対象範囲

- 単一プロジェクト（テスト対象プロダクト）内における、複数機能・複数セッション・複数 workflow を横断した観察シグナルの抽出、法則性候補の帰納分析・永続化・横断検索・再評価、および既存 owner への引き継ぎ。
- 指定ディレクトリへの決定論的保存・検証経路、ハーネスが提供する信頼境界、および `qa-workflow` / `owner_verifiers.py` / `runtime_contract.py` への統合契約。

### 1.3 対象外（Non-Goals）

- 新しい Authority 体系（第二の仕様正本）の作成。
- ユーザー回答の裁定・承認・正式決定（`DEC-xxx`）や暫定仮定（`ASM-xxx`）の正本更新（既存 owner の責務）。
- 独自のデータベース・ベクトルDB・Embedding検索・独自CAS・分散transaction基盤・プロジェクト全体ロック・グローバル連番管理・中央インデックス・常駐監視プロセスの新設。
- 特定ハーネス（`.codex/hooks/` 等）に依存した強制実行機構。
- Skillによる案件識別/切替・保存方式/Provider/ブランチ選択・認証方式選択・配置管理。必要な環境境界は外部入力とし、不要な管理は削除する。
- 複数プロジェクトを横断する汎用ナレッジの共有。

---

## 2. 現行実装と追加要件の差分

| 要件領域                     | 現行実装の仕様・制約                                                                                                                                                                                                                                                                                                                                                                                              | 本設計での対応方針（再利用／拡張／新規）                                                                                                                                                                                                                                                              |
| :--------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **保存・認可入口** | 既存 `artifact_store.py` / `git_artifact_store.py` は保存種別・revision境界を規定する（現行実装の調査対象）。 | **既存helper優先**：指定root内の相対ref、条件付き保存、履歴、独立readbackを利用する。保存技術の選択・認可はハーネス/保存層。既存store拡張や新規保存基盤を必須としない。 |
| **確定QA知識・検索**         | `qa-knowledge` は確定QA知識のみ保存（未検証Findingや仕様候補は不可）。`lookup()` は `scope_refs` の一致で絞り込むため横断検索不可。                                                                                                                                                                                                                                                                               | **再利用＋新規**: 確定QA知識の保存は `qa-knowledge` を再利用。未確定の観察・候補・実行記録の保持と、scope を越えた2段階の横断検索を新規設計する。                                                                                                                                                     |
| **仕様根拠・Authority管理**  | `spec-analysis`（`SPEC` / `DEC` / 承認済み `ASM` / `INFERENCE` / `UNKNOWN`）、`authority-resolution.md`。                                                                                                                                                                                                                                                                                                         | **再利用**: 新規スキルは仕様を確定・上書きしない。適用範囲・補足/上書き/置換・有効性は `spec-analysis` の既存契約に従う。                                                                                                                                                                             |
| **質問管理・UNKNOWN参照**    | `question-analysis`（4分類、回答正規化、再開制御）、`question_ids.py` は仕様 UNKNOWN 参照が現行 `UNKNOWN` に存在することを強制検証。                                                                                                                                                                                                                                                                              | **再利用＋連携**: 候補 identity を UNKNOWN の代わりに渡さない。仕様不明点は `spec-analysis` で正規 `UNKNOWN` として正規化してから質問化する。                                                                                                                                                         |
| **追加調査・実観測**         | `spec-analysis`、`test-target-inspection`、`ui-target-analysis`、`exploratory-testing`（`investigation`）。`exploratory_runtime.py` には handoff 先制約あり。                                                                                                                                                                                                                                                     | **再利用**: 既存成果物を読み取る形で連携し、`exploratory_runtime.py` の handoff 制約を壊さない。調査終了条件と一時障害からの再開条件を分離する。                                                                                                                                                      |
| **workflow 完了判定・検証**  | `workflow_runtime.py` は `workflow_scopes` 内の全 scope を検証。`owner_verifiers.py` と `OWNER_VERIFIED_SKILLS` の一致が必要。`_stored_owner_artifact()` は保存本文トップレベルの `artifact_ref` と scope target の一致および canonical JSON の hash 一致を検証。                                                                                                                                                 | **既存拡張**: 補助実行（scope外）と必須工程（独立完了対象 scope）を分離。3成果物すべてをトップレベル `artifact_ref` 付きの canonical JSON で永続化し、実 provider readback を host 経由で `owner_verification` へ渡す。既存共通処理で回る限り `workflow_runtime.py` 自体は変更しない。                |
| **鮮度・変更伝播・効率評価** | `artifact_graph.py` の `compare_used_context()` が `content_identity` で依存変化を判定。`workflow_efficiency.py` は2群比較（`baseline` / `candidate`）の `qa-workflow-efficiency-v1` 契約（必須5シナリオ）。                                                                                                                                                                                                      | **再利用＋組み合わせ**: 既存根拠の変化判定は `content_identity` と Authority 有効性変化を踏襲。効率評価は既存2群比較 schema（5シナリオ）を維持し、2群比較の組み合わせ＋横断継続利用の補助評価で3構成を比較する。                                                                                      |

---

## 3. Skill構成の比較と選定理由

### 3.1 構成案の比較（※負荷・コスト評価は実測前の設計予測）

| 比較項目                            | 既存Skill拡張のみ  | 新規1スキル（`context-rule-synthesis`） | 新規2スキル（`context-signal-audit` + `context-rule-synthesis`） | 新規3スキル（旧案：+ `verification`） |
| :---------------------------------- | :----------------- | :-------------------------------------- | :--------------------------------------------------------------- | :------------------------------------ |
| 横断分析の責務明確さ                | 低（既存が肥大化） | 高                                      | 高                                                               | 高                                    |
| 既存 owner との重複                 | 調整が複雑         | 最小                                    | 小                                                               | 大（`spec-analysis` 等と重複）        |
| 1ターンあたりの認知負荷（設計予測） | 高                 | 中（抽出と帰納が混在）                  | 低（高頻度軽量抽出と低頻度深い帰納を分離）                       | 低（ただし連携コスト過大）            |
| workflow 全体の総処理量（設計予測） | 小                 | 中                                      | 引継ぎ・再取得分が増加し得るため要実測                           | 大                                    |
| モード分岐の回避                    | 困難               | やや困難                                | 容易（1スキル1役割）                                             | 容易                                  |
| CI・評価の追加負荷                  | 小                 | 中                                      | やや大（A/B両方にTrigger＋Semantic評価が必要）                   | 大                                    |

### 3.2 選定結果：**新規2スキル構成を採用**（3構成実測で最終検証）

- 高頻度・軽量な「観察事実の抽出と不変ログ化（`context-signal-audit`）」と、必要時・低頻度な「複数仮説の帰納・比較・反例分析・owner振り分け（`context-rule-synthesis`）」を分離し、モード分岐を避けつつ作業あたりの認知負荷を下げる。
- 第13章の比較評価（導入前／1スキル／2スキル）で、1ターン負荷・workflow全体負荷・処理時間・分析品質を実測して最終採否を検証する。

---

## 4. 各Skillの責務・入出力契約

### 4.1 スキルA：`context-signal-audit`（軽量監査・観察事実抽出）

- **責務**: 決定論的な未処理入力判定を契機に起動し、①直前成果物から他機能へ横展開しうる**中立的な観察事実（シグナル）**を抽出し、**実取得範囲が確定した正常抽出時のみ**不変の `context-signal-batch` として永続化する、②関連する既存候補が提供された場合は潜在的な反例・再評価対象を検知する、③スキルBの優先起動が必要かを判定する。
- **重要原則**:
  - **中立的抽出の共通利用**: 抽出責務を中立的な事実抽出に限定することで、同一成果物・同一実取得範囲のバッチは分析観点に依存せず共通利用する（結果の意味を変える観測条件がある場合のみ `observation_condition` として identity に含める）。
  - **失敗試行の扱い（第4ストアを作らない）**: 取得失敗・実取得範囲未確定の部分取得・抽出失敗・保存失敗は不変バッチに書き込まず、既存の workflow state（実行ステータス：`unexecuted | fetch_failed | partial | extract_failed | persist_failed | completed`）で記録し、正常再実行を妨げない。
  - **事実と評価の分離**: 中立的な観察事実のみを記録し、仮説が存在しない段階で支持／反例の分類を強制しない。
  - **照合未実施と反例なしの区別**: 既存候補 metadata が未提供・取得不能だった場合は `candidate_check.status: "not_checked"` と記録する。
- **やらないこと**: ユーザー回答の裁定・承認、正本更新、複数成果物の深い帰納分析、プロジェクト全体のコード探索。

#### 入出力契約（`context-signal-audit`）

- **必須入力**: 指定成果物root・許可入力ref、`workflow_ref`・対象 scope・環境・バージョン、直前成果物（`source_artifact_ref`・`source_revision`・`source_content_hash`・要求調査範囲・実取得範囲・本文）、情報源の取得完全性（`complete | partial | failed`）。
- **任意入力**: 横断属性で絞り込まれた関連既存候補メタデータ（未提供時は `not_checked`）。
- **出力**: 正常抽出時の不変 `context-signal-batch`（canonical JSON、第7.2節）、照合状態とスキルB優先起動判定（失敗時は workflow state への試行状態記録）。

### 4.2 スキルB：`context-rule-synthesis`（横断法則抽出・複数仮説比較・owner振り分け）

- **責務**: 適切な分析契機（第5.1節）に起動し、未処理シグナルバッチ・過去シグナルバッチ（別観点の再利用含む）・既存候補・関連既存成果物（仕様書・`DEC`・`ASM`・過去回答・Knowledge・Observation/Finding）を横断分析し、1候補＝1独立仮説の単位で候補成果物を更新し、既存 owner へ引き継ぐ。また、**新機能の QA 開始時**に関連する既存根拠・知識・候補を横断検索して適用可能性・鮮度を確認する。
- **完了証明の単位**: 候補更新が0件の場合も含め、実行ごとに **`context-synthesis-run`（スキルB実行記録・canonical JSON）** を拡張 provider 上の正本として保存し、workflow 側から参照する。

#### 入出力契約（`context-rule-synthesis`）

- **必須入力**: 指定成果物root・許可入力ref・`workflow_ref`、要求された分析範囲（scope・分析観点・横断属性・環境・バージョン）、対象シグナルバッチ群・既存候補群・前回実行記録、関連する既存仕様根拠（`SPEC`/`DEC`/`ASM`）・過去回答（`Q-xxx`）・Knowledge、検索条件・取得完全性。
- **出力**: `context-synthesis-run`（第7.4節）、`context-rule-candidate` 更新内容（第7.3節）、既存 owner へのハンドオフ指示。

---

## 5. ワークフローと実行条件（`qa-workflow` 統合契約）

### 5.1 非循環な起動判定とBの低頻度実行制御

高頻度なAと低頻度なBの分離効果を活かすため、**「Aが動くたびに毎回Bを起動する」設計を避け、実行頻度を制御**します。

| 判定・契機                                                | 担当              | 実行方針                                                                                                                                                                                                                                                                                                                                   |
| :-------------------------------------------------------- | :---------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **スキルAの起動判定**                                     | **決定論的処理**  | 未処理の入力成果物がある、`source_content_hash` が変化した、または前回が取得失敗／部分取得／抽出失敗／保存失敗で完全バッチ未保存の場合に起動。                                                                                                                                                                                             |
| **スキルAの結果が「完全確認済み・抽出0件」**              | **制御（B不要）** | 原則としてスキルBを起動しない。                                                                                                                                                                                                                                                                                                            |
| **スキルAが通常の新規観察を抽出（または `not_checked`）** | **制御（蓄積）**  | 即時Bを起動せず不変バッチとして蓄積し、次回の適切な分析契機（下流設計前、蓄積条件到達、新機能QA開始時など）にまとめてBで処理する。`not_checked` の観察は仕様根拠確定や下流テスト設計の直前には先送りせず確実に分析する。一度Bで処理された後は、**最新の完了済み `context-synthesis-run` の処理済み集合と照合して再起動ループを防止**する。 |
| **スキルBを優先・即時起動する契機**                       | **スキルB**       | ①既存仕様・候補への重大な反例・競合を検知した場合、②仕様根拠確定・下流テスト設計の直前（未処理 `not_checked` を含む）、③新機能の QA 開始時（横断検索）、④蓄積条件到達時、⑤ユーザー明示指示時。                                                                                                                                             |

### 5.2 再利用（スキップ）条件と有効性変化の検知

以下の**すべて**を満たす場合のみ保存済み結果を再利用する（保存先全体のrevision単独ではなく内容ハッシュ・snapshot・Authority 有効性で判定）：

1. 入力成果物の `source_content_hash` が不変であり、要求範囲・分析観点・環境条件が前回完了済み `context-synthesis-run` と一致している。
2. 許可 root 配下の対象シグナルバッチ一覧に、今回の要求範囲・観点で未処理のバッチがない。
3. 関連候補および直接参照した既存成果物の内容ハッシュが不変であり（**自身が更新した候補については、`current_content_hash == confirmed_result.content_hash` の場合のみ計画済み更新とみなし、異なれば外部変更として再評価対象とする**）、かつ**本文不変でも上位 `DEC` 上書き・`ASM` 失効・Knowledge 置換・対象 build/環境/権限変化・Machine Entity fingerprint 変化がない**。
4. 前回未確認だった情報源の取得可能化や新規反例の追加がない。

### 5.3 機能有効化・補助実行／必須工程化の切替と `owner_verifiers` 契約

| 設定・要求モード                | 適用条件                                                  | `requested_scopes` / `workflow_scopes` | 保存先・認可未設定時および失敗時の扱い                                                                                                                      |
| :------------------------------ | :-------------------------------------------------------- | :------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **通常の既存 workflow（無効）** | 機能無効・無指定                                          | 追加しない                             | 補完機能を起動せず、既存 workflow の挙動・負荷を一切変えない。                                                                                              |
| **補助実行モード**              | 補助機能として有効                                        | 追加しない                             | 未設定時は推測保存せず `not_configured`、失敗時は補完を「未完了」と独立記録。既存 QA 成果物の完了判定を破損させない。                                       |
| **必須工程モード（明示要求）**  | `requested_scopes` に明示指定、またはプロジェクト必須設定 | `requested_scopes` に明示指定          | **未設定であっても黙って除外せず、該当 scope を未完了・`blocked` とする**。`owner_verifiers.py` と `OWNER_VERIFIED_SKILLS` 同期により正式な完了対象とする。 |
| **単体実行（ユーザー明示）**    | ユーザーが明示指示                                        | 指定スキルのみ                         | 未設定時は実行条件不足として停止。指定成果物に同一の verifier 契約を適用。                                                                                  |

#### 必須工程・単体実行時の完了判定と `owner_verifiers` 契約

- **実 provider readback とトップレベル `artifact_ref` 整合**: 信頼された host が実 provider の readback（canonical JSON 保存本文・hash・`artifact_ref`）を取得して `normalized_input.owner_verification` へ渡す。3成果物すべてにトップレベル `artifact_ref` を保持し、`_stored_owner_artifact()` の `artifact["artifact_ref"] == target` 検証に適合させる。AIの自己申告は完了証拠としない。
- **複数入力成果物の検証**: スキルAの必須 scope が複数の入力成果物を対象とする場合、単一バッチの検証だけで要求範囲全体を完了とせず、全対象入力の完了を確認する。
- **完了条件の厳密化**:
  - 取得不完全（`partial` / `failed`）や抽出失敗を記録しただけでは必須工程を完了扱いしない。
  - **引継ぎの成立判定**: 調査依頼の引き継ぎや質問成果物の保存が成立していれば分析工程は完了可能だが、引継ぎ先への到達・保存が確認できない（`pending` / `blocked_unverifiable`）、または必須引継ぎが認可不足で失敗した場合は要求範囲に応じて未完了とする。全仮説の正式仕様確定までは要求しない。
- **検証項目（A・B共通）**: canonical identity 再計算一致、トップレベル `artifact_ref` と scope target・identity の対応一致、canonical JSON 保存本文の hash と実 provider readback 一致、許可 root/パス境界一致、入力範囲・snapshot 整合、0件完了理由・予定集合・引継ぎ成立・取得完全性（`complete`）の確認。
- **既存 runtime 保護**: 既存共通処理で回る限り `workflow_runtime.py` 自体は変更しない。

---

## 6. 法則性抽出の具体的な分析手順（品質担保ルール）

スキルB（`context-rule-synthesis`）は、以下の11ステップを順に実行する。

1. **対象情報の取得と完全性・snapshot 記録**: 許可 root 境界内から未処理および関連する過去シグナルバッチ、既存候補、関連既存成果物（仕様書・`DEC`・`ASM`・過去回答・Knowledge・調査成果物）を取得し、復元可能な根拠集合 snapshot（全直接参照ソースを含む）と `scan_completeness` を `context-synthesis-run` に記録する。
2. **中立的な観察事実の整理と再取得の区別**: 不変バッチの観察事実および直接参照ソースを整理し、同一コンポーネント・同一仕様書由来および元成果物改訂に伴う同一観察の再取得を `independence_group` で束ね、新規の独立根拠として重複計上しない。
3. **複数仮説の生成と比較（差異条件・1候補＝1仮説）**: 共通点だけでなく「挙動の違いを生む条件」を抽出する。複数条件が相関して一意に決まらない場合は、それぞれ独立候補として並立起票し `related_candidate_refs`（`competing_hypothesis` / `alternative`）で相互参照させ、判別調査を特定する。
4. **候補ごとの証拠評価（5分類）**: 候補ごとに各観察・直接参照根拠を「支持／反例／未観察／判定不能（権限不足・非同期・環境制約等）／対象外」に分類する。未観察を否定と誤認しない。
5. **意味決定条件と適用範囲の整合**: 主張の成立を決定づける条件を `identity_key.governing_conditions`（正本）へ構造化し、`applicability`（表示・説明・検索属性）と矛盾しないことを確認する。
6. **根拠の独立性と強さの評価**: 観察件数で根拠の強さを測らない。有効な正式仕様・正式決定は観察件数に関わらず上位とするが、適用範囲・補足/上書き/置換・現在の有効性は `spec-analysis` の既存 Authority 解決契約に従う。
7. **反例の厳密な分類（無理な確定を禁止）**: 反例は ①`scope_difference`、②`impl_bug_candidate`、③`spec_change`、④`observation_condition`、⑤`hypothesis_error`、⑥`unclassified`（根拠不足のため原因未判別）に分類し、根拠不足のまま例外仕様化しない。
8. **既存 Authority・過去候補・過去回答・却下履歴との照合**: 既存正本・却下済み候補（否定条件／非否定条件）と照合する。未承認ユーザー回答（`unapproved_user_response`）は正式決定にも確定却下にも昇格させない。重複候補は第11章の並行安全手順で収束させる（安全に統合できない場合は独立保持する）。
9. **法則の性質分類と実装構造・正式仕様の分離**: 業務ルール・UI仕様・データ不変条件・状態遷移・権限制御（→`spec-analysis`）、実装共通構造（→`test-target-inspection`/`ui-target-analysis`）、不具合傾向（→`test-analysis`/`qa-knowledge`）、環境制約（→`project-context`/`qa-knowledge`）、テスト実施手順（→`qa-knowledge`）に振り分ける。
10. **追加調査の必要性と終了／再開条件の判定**: `no_new_info` の既調査は繰り返さず、一時障害による `blocked` は障害解消時に再開可能とする（第9.1節）。
11. **予定集合の確定・候補更新・実行記録の完了**: 復元可能な候補案本文（`planned_payload`）・`planned_content_hash`・`base_content_hash`・保存要求メタデータ（`write_request_meta`）を `context-synthesis-run.triage_plan` に確定保存してから各候補を更新・readback 照合し、全件確認後に実行記録を完了する。既存正本は直接書き換えない。

---

## 7. シグナル・候補・実行記録のデータ契約（Canonical JSON 永続化）

> **永続化形式と簡素化の原則**
>
> - 既存の `owner_verifiers` 契約と整合させるため、3成果物の永続化形式はすべて **トップレベル `artifact_ref` 付きの canonical JSON** とする。
> - 既存情報から導出できる値や外部検証結果（`signal_count`、`persistence_verified`、`completed_and_readback_verified` 等）は正本フィールドとして持たず、二重管理・不整合を防ぐ。
> - `artifact_ref` と identity の対応は `<kind>/<identity>.json` のように決定論的に一意対応させる（詳細パス規約は実装Planで確定）。 ref/identityは指定root内で比較する。新規本文に案件IDを必須としない。

### 7.1 4種識別子（Identity）と一貫性契約

| 識別対象                                          | 構成要素（正規化構造化キー）                                                                                                                                                                | 役割・一貫性契約                                                                                                                                                                                                                                     |
| :------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. 法則性候補（`candidate_identity`）**         | `identity_key`（指定root内）（`domain`, `operation_axis`, `rule_kind`, `target_scope_kind`, `governing_conditions`［意味決定条件の正本］, `assertion_polarity`, `normalized_assertion`） | 決定論的 helper が `identity_key` からハッシュ生成。`identity_key` を成果物内に保持して再計算検証し、`applicability` との構造的一致を helper、意味的一致を AI が検証する。検索タグの追加では identity を変えない。                     |
| **2. 観察事実（`signal_identity`）**              | `source_artifact_ref` ＋ `observation_locator`（同一セクション内の複数ルールを区別できる粒度＋元成果物に含まれない観測条件）＋ `source_content_hash`                                        | 決定論的 helper が生成。各シグナルの `signal_content_hash` も算出し、候補側の参照整合性を担保する。                                                                                                                                                  |
| **3. 実行・再開識別（`workflow_operation_id`）**  | `workflow_ref` ＋ 処理対象 ref 群 ＋ 操作種別 ＋ **要求範囲（scope・分析観点・調査条件・環境）** ＋ 入力 content hash 群                                                                    | 同一成果物でも要求範囲や分析観点が異なれば別操作として識別し、誤った完了再利用を防ぐ。CAS競合後に更新内容が変わる場合や再認可時は、保存層の再送fingerprintの不一致 を避けるため新しい `operation_id` を発行し、単純再送と新判断を区別する。 |
| **4. 意味的引継ぎ識別（`semantic_handoff_key`）** | `target_owner` ＋ `target_scope` ＋ 正規化された反映意図ハッシュ（`normalized_intent`）※`workflow_ref`・`candidate_identity` 非依存                                        | 異なる workflow や候補統合・identity 置換後であっても、既存 owner に対する同一の意味的反映を識別する。生成元（`target_scope`・`normalized_intent`）を `handoff_records` に保持して再計算・内容復元を可能にする。                                     |

### 7.2 シグナルバッチ（`context-signal-batch`）：正常抽出専用の完全不変ログ

実取得範囲が確定した正常抽出時のみ保存する完全不変ログ。**要求範囲（`requested_range`）と実取得範囲（`actual_inspected_range`）を分離し、`batch_identity` に `actual_inspected_range`（および結果の意味を変える観測条件がある場合のみ `observation_condition`）を含める**ことで、部分取得後の完全取得でも identity が衝突しない。実取得範囲を確定できない部分取得や抽出失敗は不変バッチに保存せず、workflow state の試行記録に留める。

```json
{
  "schema_version": "1.0",
  "artifact_ref": "<許可サブディレクトリ>/context-signal-batch/<batch_identity>.json",
  "batch_identity": "<deterministic-hash: source_artifact_ref + source_content_hash + actual_inspected_range + observation_condition>",
  "workflow_operation_id": "<op-id>",
  "source": {
    "artifact_ref": "<sanitized-ref>",
    "source_revision": "<rev>",
    "source_content_hash": "<sha256>",
    "requested_range": "<all | normalized section/path list>",
    "actual_inspected_range": "<all | 実際に取得・確認できた正規化範囲>",
    "observation_condition": "<null | 結果の意味を変える観測条件>"
  },
  "scan_completeness": "complete | partial",
  "candidate_check": {
    "status": "checked_with_triggers | checked_no_conflict | not_checked",
    "triggered_candidate_identities": ["<candidate-id>"]
  },
  "signals": [
    {
      "signal_identity": "<deterministic-signal-id>",
      "signal_content_hash": "<sha256-of-normalized-signal>",
      "observation_locator": "<section/rule-item/element + observation-condition>",
      "evidence_type": "spec | decision | approved_asm | unapproved_user_response | impl_observation | exploratory_finding",
      "fact_summary": "<機密・個人情報除外済みの中立的観察事実>",
      "independence_group": "<同一コンポーネント・同一仕様書・同一観察再取得の束ねキー>",
      "cross_cutting_attributes": {
        "operations": ["delete"],
        "domains": ["user"],
        "roles": ["admin"],
        "channels": ["ui"],
        "data_states": ["permanent_delete"]
      },
      "environment_and_versions": [
        { "environment": "staging", "version_constraint": "v2.x" }
      ],
      "unapproved_response_meta": {
        "responder_role": "<role>",
        "approval_status": "unapproved",
        "question_ref": "Q-xxx",
        "question_revision": "<rev>",
        "scope_ref": "<scope>"
      }
    }
  ]
}
```

### 7.3 候補成果物（`context-rule-candidate`）：1候補＝1独立仮説

```json
{
  "schema_version": "1.0",
  "artifact_ref": "<許可サブディレクトリ>/context-rule-candidate/<candidate_identity>.json",
  "candidate_identity": "<deterministic-hash: identity_key>",
  "identity_key": {
    "domain": "resource_lifecycle",
    "operation_axis": "delete",
    "rule_kind": "ui_confirmation",
    "target_scope_kind": "permanent_delete",
    "governing_conditions": {
      "roles": ["admin"],
      "channels": ["ui"],
      "data_states": ["permanent_delete"],
      "environment_and_versions": [
        { "environment": "staging", "version_constraint": "v2.x" }
      ]
    },
    "assertion_polarity": "required",
    "normalized_assertion": "confirmation_dialog_before_permanent_delete"
  },
  "rule_statement": "<構造化された法則性候補・差異条件>",
  "applicability": {
    "scope_summary": "<適用対象（governing_conditions と整合）>",
    "cross_cutting_attributes": {
      "operations": ["delete"],
      "domains": ["user", "project"]
    },
    "invalidation_conditions": ["ゴミ箱への移動など復元可能な場合"]
  },
  "related_candidate_refs": [
    {
      "candidate_identity": "<other-candidate-id>",
      "relation": "competing_hypothesis | alternative | replaced_by | merged_into | split_into"
    }
  ],
  "evidence_links": [
    {
      "link_kind": "signal_ref | direct_source_ref",
      "signal_batch_ref": "<batch-ref | null>",
      "signal_identity": "<signal-id | null>",
      "signal_content_hash": "<sha256 | null>",
      "direct_source_ref": "<spec/dec/asm/knowledge/answer ref | null>",
      "direct_source_revision": "<rev | null>",
      "source_content_hash": "<sha256>",
      "evaluation": "supports | counterexample | indeterminate | out_of_scope",
      "counterexample_classification": "scope_difference | impl_bug_candidate | spec_change | observation_condition | hypothesis_error | unclassified | null"
    }
  ],
  "unobserved_ranges": ["一般ユーザー権限での完全削除"],
  "currentness_dependencies": [
    {
      "target_ref": "<spec/dec/asm/code/knowledge/authority-resolution ref>",
      "dependency_content_hash": "<sha256>",
      "effective_authority_fingerprint": "<sha256 | null>",
      "source_revision": "<rev>",
      "dependency_freshness": "current | changed | unverifiable | deleted"
    }
  ],
  "evaluation_status": {
    "scan_completeness": "complete | partial | failed",
    "revalidation_required": false,
    "revalidation_reasons": [],
    "last_synthesis_run_ref": "<run-ref>"
  },
  "resolution_state": "uninvestigated | investigating | resolved | rejected | deferred | superseded | blocked",
  "resolution_links": [
    {
      "owner": "spec-analysis | project-context | qa-knowledge | test-analysis | test-target-inspection | ui-target-analysis | defect-management",
      "artifact_kind": "SPEC | DEC | ASM | PROJECT_CONTEXT | KNOWLEDGE | PRODUCT_RISK | INSPECTION | DEFECT",
      "artifact_ref": "<canonical-ref>",
      "artifact_revision": "<rev>",
      "artifact_content_hash": "<sha256>",
      "coverage": "full | partial"
    }
  ],
  "implementation_conformance_refs": [
    {
      "scope_ref": "<feature-scope>",
      "environment": "staging",
      "build_ref": "<build>",
      "status": "conforms | confirmed_mismatch | unverified",
      "ref": "<fail/finding/investigation ref>",
      "revision": "<rev>",
      "verified": true
    }
  ],
  "question_refs": [
    {
      "unknown_ref": "UNK-xxx | null",
      "question_id": "Q-xxx",
      "question_artifact_ref": "<ref>",
      "question_revision": "<rev>"
    }
  ],
  "handoff_records": [
    {
      "semantic_handoff_key": "<deterministic-hash: target_owner + target_scope + normalized_intent>",
      "workflow_operation_id": "<op-id>",
      "target_owner": "<owner-skill>",
      "target_scope": "<scope>",
      "normalized_intent": "<再計算・復元用の正規化された反映意図・要求内容>",
      "reason": "<機密除外済みの引継ぎ理由>",
      "status": "pending | confirmed_by_readback | returned | blocked_unverifiable",
      "confirmed_target_ref": {
        "artifact_ref": "<ref | null>",
        "artifact_revision": "<rev | null>",
        "artifact_content_hash": "<sha256 | null>"
      }
    }
  ],
  "rejection_or_deferral_detail": {
    "reason": "<理由>",
    "authority_basis_ref": "<判断根拠ref・revision・判断主体>",
    "negated_conditions": ["すべての削除操作に一律適用すること"],
    "non_negated_conditions": ["復元不能な削除操作のみへの適用"],
    "scope_at_decision": "<判断時の適用範囲>"
  },
  "investigation_history": [
    {
      "target_skill": "<skill>",
      "source_ref": "<ref>",
      "source_content_hash": "<sha256>",
      "condition_hash": "<調査条件>",
      "outcome": "resolved | no_new_info | blocked_transient | blocked_permission | blocked_env | blocked_safety",
      "resume_condition": "<再開条件>"
    }
  ]
}
```

- ※ **参照関係の循環ルール**: 自己参照は一律禁止。循環参照の禁止は後継関係をたどる `replaced_by` / `merged_into` / `split_into` にのみ適用し、比較対象の `competing_hypothesis` / `alternative` の相互参照は許容する。

### 7.4 スキルB実行記録（`context-synthesis-run`）：拡張 provider 上の正本

0件完了証明・全根拠集合 snapshot・復元可能な予定更新内容（`planned_payload`）を一元管理する正本（workflow 側から参照）。

```json
{
  "schema_version": "1.0",
  "artifact_ref": "<許可サブディレクトリ>/context-synthesis-run/<run_identity>.json",
  "run_identity": "<deterministic-hash: workflow_operation_id>",
  "workflow_operation_id": "<op-id>",
  "requested_scope": {
    "scope_refs": ["<scope>"],
    "analysis_aspect": "<例: 権限制御 / 削除操作 / 全般>",
    "environment_and_versions": [
      { "environment": "staging", "version_constraint": "v2.x" }
    ]
  },
  "inspected_scope": "<実際に調査した範囲>",
  "scan_completeness": "complete | partial | failed",
  "snapshot": {
    "snapshot_hash": "<sha256>",
    "search_roots_and_scopes": ["<root/scope>"],
    "search_criteria": "<横断属性・同義概念の絞り込み条件>",
    "referenced_sources": [
      {
        "source_kind": "signal_batch | candidate | spec | decision | asm | question_answer | knowledge | inspection_or_finding | authority_resolution",
        "artifact_ref": "<ref>",
        "source_revision": "<rev>",
        "content_hash": "<sha256>",
        "effective_authority_fingerprint": "<sha256 | null>"
      }
    ],
    "unverifiable_sources": ["<取得不能な情報源ref>"],
    "excluded_scope_notes": "<対象外とした範囲>"
  },
  "triage_plan": {
    "target_batch_refs": ["<今回処理対象のバッチref>"],
    "planned_candidate_ops": [
      {
        "candidate_identity": "<id>",
        "candidate_ref": "<artifact_ref>",
        "action": "create | update | merge_into | split_into | reuse",
        "base_content_hash": "<分析開始時の候補本文hash | null>",
        "expected_revision": "<SQLite用または取得時storage_revision | null>",
        "operation_id": "<provider書込み用operation_id>",
        "planned_content_hash": "<planned_payload の canonical JSON sha256>",
        "planned_payload": {
          "...": "中断後に復元可能な候補案本文（reuse時はnull）"
        },
        "write_request_meta": {
          "source_ref": "<ref>",
          "source_revision": "<rev>",
          "approval_ref": "<ref>",
          "approval_revision": "<rev>",
          "change_reason": "<機密除外済みの変更理由>"
        },
        "confirmed_result": {
          "artifact_ref": "<ref | null>",
          "storage_revision": "<rev | null>",
          "content_hash": "<sha256 | null>"
        }
      }
    ]
  },
  "result_summary": {
    "status": "in_progress | completed | completed_zero_changes | blocked_incomplete",
    "zero_change_reason": "no_related_candidates | existing_candidates_sufficient | all_evidence_known | empty_search | null",
    "unresolved_and_handoff_refs": ["<handoff/question ref>"]
  }
}
```

- ※ 完了確認は `confirmed_result.content_hash == planned_content_hash`（実 provider readback 由来）の照合で行い、再開時は `planned_payload` と `write_request_meta` から保存要求を復元する。

### 7.5 状態遷移契約（7状態の維持）

| 状態             | 主な遷移元                                                          | 遷移トリガー・条件                                                                                                                                                                                                                                              |
| :--------------- | :------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `uninvestigated` | （新規）                                                            | スキルBが新規シグナルから独立仮説として起票。                                                                                                                                                                                                                   |
| `investigating`  | `uninvestigated` / `resolved` / `rejected` / `deferred` / `blocked` | 追加調査開始、質問発行、owner引継ぎ、または `revalidation_required == true`・一時障害解消・保留論点の合否必須化による再評価開始。                                                                                                                               |
| `resolved`       | `uninvestigated` / `investigating`                                  | 既存 owner の正式成果物への反映を readback 確認。`resolved` は候補処理の終了を示し、正式仕様確定か暫定ASMかリスク採用かは `resolution_links.artifact_kind` と正本で判別する。継続調査段階の一部裏付けは `coverage: partial` のまま `investigating` を維持する。 |
| `rejected`       | `investigating`                                                     | 既存 owner が有効な根拠（`authority_basis_ref`）に基づき否定。未承認回答のみでは却下しない。                                                                                                                                                                    |
| `deferred`       | `uninvestigated` / `investigating`                                  | 当面の合否判定に不要と判断し保留。後続 QA で必須化すれば revision 不変でも `investigating` へ戻す。                                                                                                                                                             |
| `superseded`     | 任意                                                                | 統合・置換・必要時の分割において、**継承先の保存＋readback 完了、継承先が依然有効で根拠を保持していること、および旧候補の本文・revision 一致を確認後にのみ**遷移（第11章）。                                                                                    |
| `blocked`        | `investigating`                                                     | 権限不足・認証失敗・一時障害・取得不能・安全承認待ち・owner側冪等性未保証・統合時の整合性未保証等で進行不可。                                                                                                                                                   |

---

## 8. 永続化・認可・横断検索・再評価の契約

### 8.1 ディレクトリ管理と責務分離

成果物は指定rootの相対ディレクトリで管理する。外部からの実行条件・許可rootを受け取り、以下の分離を守る。既存helperを優先し、具体的な保存能力は詳細Plan 01で確認する。

1. **Skill A / B**: 観察抽出・帰納分析・反例・必要質問とowner振り分け、保存候補canonical JSONの生成。案件/保存技術/認証方式を判断しない。
2. **決定論的 production helper**: 4種 identity 再計算・トップレベル `artifact_ref`・schema・状態遷移・`governing_conditions` 構造一致・機密除外・snapshot 整合の検証。
3. **ハーネス/信頼境界**: 必要なroot・実行条件・権限・操作許可・失効確認を提供する。AI自己申告やダミー認可を本番証拠にしない。特定製品のハーネスに依存しない。
4. **決定論的保存層**: 指定root内のkind別ディレクトリへ条件付き作成/更新、履歴、独立readback。実保存証拠を既存 `owner_verification` へ提供する。必要能力が未確認なら該当操作をblock。

- **共有境界**: 同一保存実体・許可root・同時更新保証は外部で確認する。別rootの同一相対refを同一正本とみなさない。既存正本の無断移行は禁止。
- **並行更新と自己競合**:
  - 保存対象・依存先の変更と、無関係な保存先revision変化を区別する。保存技術の実装詳細はSkillに持たせない。
  - 保存直前に `base_content_hash`・関連依存・認可を照合し、対象と依存が変わっていないことを条件付き保存で保証する。前提変化は意味判断をやり直す。保証不能なら局所blockし、独自lock・分散transactionを新設しない。

### 8.2 シグナルの不変性・分析観点別の再利用・トリアージ再開

- `context-signal-batch` は実取得範囲が確定した正常抽出結果のみを保存する完全不変ログとする。
- スキルBは、要求範囲・分析観点（`requested_scope.analysis_aspect` 等）が一致する完了済み `context-synthesis-run` の `triage_plan.target_batch_refs` との差分から未処理バッチを特定する。**ある観点で処理済みでも、別の観点・新しい仮説の横断分析では過去バッチを何度でも再利用できる**。
- 複数候補の更新途中で中断した場合、`context-synthesis-run.triage_plan.planned_candidate_ops` の `planned_payload`・`planned_content_hash`・`write_request_meta` を用いて実 provider の readback と照合し、未完了分のみ再開する。

### 8.3 横断検索の実現と完全性の定義

- **2段階検索**: ①発見（許可 root 配下の候補・不変バッチ・Knowledge・既存仕様/DEC/ASM/過去回答の軽量メタデータ走査＋AIによる表現ゆれ吸収）と、②既存 owner による適用可能性・鮮度確認を分離する。
- **`complete` の保証範囲**: 許可 root 列挙・指定検索条件の実行・発見対象の確認という**要求手順の完了**を保証し、指定された範囲内に未発見の関連仕様が絶対に存在しないこと（意味的網羅性）までは保証しない。検索範囲・絞り込み条件・未確認源を `snapshot` に明示する。

### 8.4 新機能 QA 開始時の再利用フローと下流への変更伝播

- **新機能 QA 開始時（6ステップ）**: ①対象特定 → ②横断発見（snapshot・完全性記録） → ③内容ハッシュおよび Authority 有効性（上位 `DEC` 上書き・`ASM` 失効・Knowledge 置換等）の照合 → ④`spec-analysis` による Authority 解決 → ⑤`question-analysis` による残存不明点のみの質問化（却下候補を理由に未定義の個別仕様質問を省略しない） → ⑥下流供給（未承認仮説は探索・調査・テスト観点候補に限定し、最終 PASS/FAIL には使用しない）。
- **下流への変更伝播**: 候補成果物自体の更新のみでは既存テスト設計を再生成しない。候補を契機として `SPEC` / `DEC` / 承認済み `ASM` / `PROJECT_CONTEXT` / `qa-knowledge` / `test-analysis` の正式な Product Risk・テスト重点が変更された場合のみ、既存 Machine Entity・依存 fingerprint に従って下流へ伝播する。

---

## 9. 既存 owner へのハンドオフと質問前の自己解決

### 9.1 追加調査ルーティングと終了／再開条件の分離

| 不足情報・調査内容                     | 担当スキル                               | 終了・再開ルール                                                                                                                                                                                                                                                                                                                                                                      |
| :------------------------------------- | :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 仕様書・決定事項・過去回答の確認       | `spec-analysis`                          | **`no_new_info`**: 同一情報源・content hash・調査条件で新情報なしと確定済みなら、情報源または条件が変わるまで再調査せず質問・保留へ移行。<br>**一時障害（`blocked_transient` / `blocked_permission` / `blocked_env` / `blocked_safety`）**: 認証回復・API復旧・権限変更・環境準備・安全承認の充足により、元情報源の revision が不変でも再開可能（固定回数の自動リトライは入れない）。 |
| 画面・実装構造・共通コンポーネント確認 | `test-target-inspection`                 | 同上                                                                                                                                                                                                                                                                                                                                                                                  |
| UI構造・画面遷移・状態の継続分析       | `ui-target-analysis`                     | 同上                                                                                                                                                                                                                                                                                                                                                                                  |
| 実操作による仮説・反例の動的検証       | `exploratory-testing`（`investigation`） | 同上（※`exploratory_runtime.py` の handoff 制約を変更せず、既存成果物を読み取る形で連携）                                                                                                                                                                                                                                                                                             |

### 9.2 判定結果ごとの既存 owner 振り分け契約

| 分析結果・状況                                                                   | 候補の扱い                                                                                                                       | 振り分け先（既存 owner）                                                                                             |
| :------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------- |
| 有効な `SPEC`/`DEC` が候補全体を裏付け、実装とも一致                             | `resolved`（`SPEC/DEC`、`conforms`）                                                                                             | `spec-analysis`（参照維持）                                                                                          |
| 有効な `SPEC`/`DEC` が候補全体を裏付け、実装は未確認                             | `resolved`（`SPEC/DEC`、`unverified`）                                                                                           | `spec-analysis`（実装確認は別管理）                                                                                  |
| 有効な `SPEC`/`DEC` が候補全体を裏付け、既存 FAIL/Finding で実装不一致が検証済み | `resolved`（`SPEC/DEC`、`confirmed_mismatch`）                                                                                   | **`defect-management`**（仕様質問に戻さない）                                                                        |
| 有効な `SPEC`/`DEC` が候補全体を裏付けるが、コード推論のみで実装不一致を疑う     | `resolved`（`SPEC/DEC`、`unverified`＋調査ref）                                                                                  | 担当調査スキルまたは `exploratory-testing`（確定FAIL扱いしない）                                                     |
| 有効な `SPEC`/`DEC` が候補の一部範囲のみ裏付ける                                 | 継続調査なら `investigating`（`coverage: partial`）を維持、独立管理が必要なら分割（旧候補を `superseded`）                       | `spec-analysis` ＋ 残余範囲の調査／質問                                                                              |
| 承認済み `ASM` による暫定解決 / 環境・実施条件の確定                             | `resolved`（`ASM` または `PROJECT_CONTEXT`）                                                                                     | `project-context` / `spec-analysis`                                                                                  |
| 実装観察のみで正式仕様が存在しない                                               | `investigating`（`INFERENCE` 扱い）                                                                                              | 追加調査スキル → 未解決なら `spec-analysis`（`UNKNOWN` 化）→ `question-analysis`                                     |
| 共通コンポーネント等の実装上の共通構造                                           | `resolved`（`INSPECTION`）                                                                                                       | `test-target-inspection` / `ui-target-analysis`                                                                      |
| 有効な `SPEC` 同士の競合、または仕様上の適用範囲・例外・合否根拠が不明           | `investigating`（`question_refs` 紐づけ）                                                                                        | `spec-analysis` で正規 `UNKNOWN` 化 → `question-analysis`（既存4分類維持・回答受領後も意味確定まで解決済みにしない） |
| 仕様 UNKNOWN に該当しない任意確認・調査相談                                      | `investigating`（`unknown_ref: null`）または `deferred`                                                                          | `question-analysis`（任意確認）                                                                                      |
| 不具合傾向・リスク候補 / 環境制約 / テスト実施手順                               | 既存知識で解決済みなら新規登録せず既存 ref を再利用。新規反映後は `resolved`（`PRODUCT_RISK` / `KNOWLEDGE` / `PROJECT_CONTEXT`） | `test-analysis` / `qa-knowledge` / `project-context`                                                                 |

---

## 10. 変更対象ファイルと既存処理の再利用方針

| 区分                 | 対象ファイル・モジュール                                                                          | 変更・再利用の内容                                                                                                              |
| :------------------- | :------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------ |
| **新規作成**         | `skills/context-signal-audit/{SKILL.md, assets/, references/, evals/trigger/, evals/semantic/}`   | スキルA本体・テンプレート・ガイド・CI必須 Trigger 評価・Semantic 評価                                                           |
| **新規作成**         | `skills/context-rule-synthesis/{SKILL.md, assets/, references/, evals/trigger/, evals/semantic/}` | スキルB本体・テンプレート・ガイド・CI必須 Trigger 評価・Semantic 評価                                                           |
| **新規作成**         | 決定論的 production helper（配置・命名は実装時に確定）                                            | 4種識別子生成・再計算、トップレベル `artifact_ref`・canonical JSON schema・状態遷移・`governing_conditions` 検証、snapshot 比較 |
| **確認・必要時のみ** | 既存決定論的保存helper | 指定rootのkind別ディレクトリ、一覧・履歴・条件付き保存・独立readback。既存store拡張を前提にしない。 |
| **確認・必要時のみ** | ハーネス/保存層の信頼境界 | 許可rootと権限の実確認、保存証拠の受け渡し。特定ハーネスの実装や認証基盤の新設は対象外。 |
| **変更必須**         | `skills/qa-workflow/SKILL.md`・`references/guidance.md`                                           | 非循環起動条件、低頻度B制御、再利用条件、未設定時無効・補助／必須モード切替、スキルA試行状態記録の明記                          |
| **変更必須**         | `skills/qa-workflow/scripts/owner_verifiers.py`・`runtime_contract.py`                            | 必須工程時の verifier 登録と `OWNER_VERIFIED_SKILLS` 同期                                                                       |
| **変更必須**         | `README.md`・`EVALS.md`・`tests/skills/runtime/`・`tests/skills/evals/deterministic/`             | CI必須記載、評価契約、並行・認可・再開・verifier 契約テスト                                                                     |
| **確認・必要時のみ** | `skills/qa-workflow/scripts/workflow_runtime.py`・`skills/project-context/`・既存 owner 群        | `workflow_runtime.py` は既存共通処理で成立する限り変更しない。既存 owner の冪等照合で不足があれば最小限の範囲で拡張する。       |

---

## 11. 異常系・並行実行・中断再開

| シナリオ                                                     | 対策契約                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| :----------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **並行 handoff（TOCTOU）による正本二重反映**                 | 既存 owner の保存単位 CAS を使用し、**CAS 競合後は必ず正本を再 readback して意味的重複の有無を再確認**する。`semantic_handoff_key`（`workflow_ref`・`candidate_identity` 非依存）を既存 owner の処理結果と対応づけ、反映済みか確認できない場合や冪等性を保証できない操作は無条件に再実行せず `blocked_unverifiable` とする。                                                                                                                                                                                                                                                                      |
| **候補統合中の並行更新（継承元・継承先双方および循環防止）** | ①継承先Yを先に保存＋readback 確認する。②旧候補Xを `superseded` に更新する直前に、**Xの `base_content_hash`（および最新 CAS revision）の一致確認に加えて、継承先Yを最新 readback し「Yが依然有効（`superseded` でない）かつ継承した根拠を保持していること」**を確認する。③Xに新規根拠・反例が追加されていた場合や、Yが別候補Zへ置換・相互統合で循環しかけている場合は、そのまま `superseded` にせず再判断する。既存 provider の native CAS で安全に整合を保証できない場合は、**分散ロックを作らず旧候補を有効なまま独立保持して統合を停止（`blocked`）する**（重複の一時残存より根拠消失を防ぐ）。 |
| **候補分割時の履歴継承と有効根拠の区別**                     | 分割元の履歴は参照（`related_candidate_refs`）で追跡可能とし、**現在有効な根拠・解決結果（正式仕様・回答等）は分割先それぞれの適用範囲を再評価して該当するものだけを適用**する。                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **保存成功・readback失敗および中断後の冪等再開**             | 保存失敗と保存結果不明（保存成功・readback 失敗）を区別する。不変バッチは再実行前に `batch_identity` で既存保存先を確認し、整合する保存済み成果物があれば再利用する。候補更新の中断再開時は `context-synthesis-run.triage_plan` の `planned_payload`・`planned_content_hash`・`write_request_meta` と実 provider readback を照合して未完了分のみ実行する。CAS 競合後に内容が変わる場合や再認可（`approval_ref` 等変更）時は、元操作結果を確認のうえ新しい `operation_id` を発行して `operation_id_reused` を防ぐ。                                                                                |
| **無関係更新と結果不明からの再開** | 対象・依存・認可不変を確認して安全な条件付き更新を行う。結果不明時は実保存先と履歴・semantic_handoff_keyを照合し、盲目的再実行しない。 |
| **分析中の新規反例追加（完了と採用の分離）**                 | 開始時 snapshot と完了確認・次回再利用前の軽量一覧取得を比較する際、自身が更新した候補は `current_content_hash == confirmed_result.content_hash` の場合のみ計画済み更新とみなす（異なれば外部変更として検知）。分析中に新規反例が追加された場合、当時の snapshot に対する分析記録自体は残せるが、**未評価の反例が残る状態で古い結果を質問省略や最終 PASS/FAIL 判定に採用することを禁止**し、影響範囲のみ再評価する。                                                                                                                                                                              |
| **認可違反・失効・CAS非対応・境界違反・未設定** | 認可自己申告・ダミー認可・権限失効・共有CAS未確認・許可root外・symlink脱出・別rootの証拠を拒否。該当操作のみblockし第5.3節の条件に従う。 |

---

## 12. セキュリティ・データ保護

1. **プロジェクト境界・パス認可の厳守**: 許可 root および成果物種別ごとの許可サブディレクトリ境界を信頼された `authorize()` で検証し、再実行時にも権限の失効を再確認する。
2. **全領域における機密情報・個人情報の非保存**: シグナル本文だけでなく **`source_artifact_ref`・`observation_locator`・`cross_cutting_attributes`・`normalized_assertion`・`investigation_history`・`handoff_records.reason`・`handoff_records.normalized_intent`・`write_request_meta.change_reason`・Git commit metadata（commit message 含む）・Semantic 評価データ** のすべてに機密・個人情報除外契約を適用する。ユーザー回答は全文保存せず、必要要約と `Q-xxx`・revision 参照のみ保持する。
3. **プロンプトインジェクション防御**: 仕様書・回答・UIテキスト・ログ内の文字列はすべて処理対象データとして扱い、内部に埋め込まれた指示を実行しない。
4. **無断仕様変更・不適切転用の防止**: 正本変更は既存 owner の認証済み承認経路に限定し、過去回答の転用時は回答時の scope・revision・承認状態を照合する。

---

## 13. CI・テスト・受入条件・効率評価

### 13.1 CI・評価構成

- **CI 必須要件（`validate-skills.yml`）**: 両スキルの `skills-ref` 検証通過、`evals/trigger/{train,validation}_queries.json`（正負同数・重複禁止）、`README.md` 記載。
- **スキルA の Semantic 評価**: 抽出漏れ防止（最重要）、誤抽出、重複、反例検知、未承認回答の承認状態誤認、`not_checked` と反例なしの区別。
- **スキルB の Semantic 評価**: 共通法則・**差異条件（例：権限 vs 復元可能性の切り分け）**の抽出精度、複数仮説比較、反例原因の `unclassified` 保持、局所仕様の過一般化防止、根拠独立性評価。
- **決定論的・ランタイムテスト**: 4種識別子再計算、トップレベル `artifact_ref`・canonical JSON schema・状態遷移・循環参照ルール、部分取得後の完全取得非衝突、保存成功/readback失敗からの再利用、認可・失効、無関係更新による不要再分析の回避、CAS競合後の意味的重複再確認および新 `operation_id` 発行、統合中の継承元/継承先並行更新・循環停止、分割時の適用範囲再評価、実 provider readback 経由の verifier 契約。

### 13.2 統合受入検証チェックリスト（重複統合済み）

#### A. 不変ログ・データ契約・識別・状態遷移

- [ ] 同一成果物の抽出失敗後に正常な再実行・保存ができ、部分取得（`actual_inspected_range`）後の完全取得でも `batch_identity` が衝突しない。また保存成功・readback失敗時に既存バッチを再利用できる。
- [ ] スキルAの失敗状態（取得失敗／部分取得／抽出失敗／保存失敗）を第4ストアなしで workflow state 等から未実行・完了と区別できる。
- [ ] 保存前に自己申告された完了フラグを証拠にせず、実 provider readback で保存完了を判定する。
- [ ] `revalidation_needed` 等の鮮度・完全性状態を `resolution_state` と混同せず、7状態＋3軸で一貫管理できる。
- [ ] `rejected`・`deferred`・`blocked`・`resolved` から、再評価トリガーや一時障害解消に応じて安全に `investigating` へ再開できる。
- [ ] 指定root内の `identity_key` から `candidate_identity` を、また `handoff_records` から `semantic_handoff_key` を再計算でき、同一法則文でも成立条件・極性が異なる候補および異なる分析 scope・調査条件の操作を区別できる。
- [ ] `competing_hypothesis` / `alternative` の相互参照を許容し、`replaced_by` / `merged_into` / `split_into` の循環および自己参照を拒否する。
- [ ] 複数仮説を独立候補として管理し一部解決を表現でき、候補更新0件のスキルB実行を `context-synthesis-run` で証明し未実行と区別できる。

#### B. 並行実行・永続化・認可・再開

- [ ] 複数 workflow が同時に未反映と判定しても、CAS 競合後の意味的重複再確認と `semantic_handoff_key` により正本を二重作成しない。
- [ ] 候補統合途中に継承元へ追加された根拠・反例を失わず、かつ継承先が置換・相互統合された場合も循環や消失を起こさず安全に停止（独立保持）できる。分割先へ適用範囲外の正式仕様や解決結果を誤継承しない。
- [ ] `planned_payload`・`planned_content_hash`・`write_request_meta` を用いて中断後の更新内容を復元・照合再開でき、CAS競合後の新判断や再認可時は新 `operation_id` を発行して元操作の再送と区別できる。
- [ ] 指定rootの異なるkindの更新で不要な再分析をせず、対象候補・依存先の真の変更を検知する。後続更新後の履歴参照・別rootの同名ref拒否・実保存能力不足の局所停止を確認する。
- [ ] 信頼された実行入口から許可済み保存を行い、認可失効、条件付き保存未確認、許可外root、自己申告・ダミー認可を拒否する。Skillに保存技術の選択をさせない。
- [ ] QA成果物書込み認可と正式仕様変更承認を区別し、許可 root 外・許可サブディレクトリ外・symlink・別rootの参照・書込みを拒否する。

#### C. 横断検索・起動制御・鮮度・再評価

- [ ] 処理済み `not_checked` バッチによってスキルBを繰り返し起動せず、完全確認済み0件バッチによって不要な深い分析を起動しない（仕様根拠確定・下流設計直前の未処理 `not_checked` は先送りしない）。
- [ ] 新機能の QA 開始時、scope が異なっていても関連する過去の法則・決定事項・Knowledge・導入前仕様・過去回答を発見でき、分析範囲が異なる過去バッチを必要時に再利用できる。
- [ ] `context-synthesis-run.snapshot` から直接参照した SPEC・DEC・ASM・Knowledge・回答を含む根拠集合を復元でき、候補単位の `evidence_links`（`direct_source_ref` 含む）と対応づけられる。
- [ ] 自身が更新した候補でも `confirmed_result.content_hash` と異なれば外部変更として検知し、分析中に新規反例が追加された場合は未評価のまま古い結果を質問省略・PASS/FAIL 判定に採用しない。
- [ ] 新規反例・独立支持根拠の追加や、本文不変での Authority 失効・置換によって再評価でき、既存観察の再取得を独立根拠として過大評価しない。
- [ ] 却下範囲外の仮説を誤除外せず、却下済み候補を理由に未解決の個別仕様質問を省略しない。

#### D. 帰納的推論・Authority・既存 owner 連携・変更伝播

- [ ] 複数根拠から共通法則と差異条件を抽出し、複数仮説を比較して判別調査を特定できる。候補照合未実施（`not_checked`）と反例なしを区別できる。
- [ ] 同じ観察事実を複数候補に対して評価でき、支持・反例・未観察・判定不能・対象外を区別し、反例原因が判別不能なら `unclassified` として保持できる。
- [ ] 同一コンポーネント・同一情報源由来の観察を過大評価せず、局所仕様を横断候補全体の確定根拠にしない。
- [ ] 実装未確認・実装不一致でも有効な `SPEC` を維持し、機能ごとの実装適合・不一致・未確認を区別できる（推論のみの不一致を確定FAIL扱いしない）。
- [ ] `PRODUCT_RISK` 採用や `ASM` 承認、`PROJECT_CONTEXT` 反映を正式仕様確定と誤認せず、未承認回答のみで不適切に昇格・却下せず、回答受領済みでも意味未解決なら解決済みにしない。
- [ ] 既存 `UNKNOWN` と `Q-xxx` の参照契約を維持し、追加実観測を `exploratory-testing`（`investigation`）へ渡せる。進捗のない調査（`no_new_info`）を終了し、一時障害解消後は再開できる。
- [ ] 候補更新のみでは不要なテスト設計再生成を起こさず、正式仕様・承認済み ASM・PROJECT_CONTEXT・Knowledge・正式な Product Risk 変更時は下流へ伝播する。

#### E. workflow 完了判定・セキュリティ・効率・回帰

- [ ] 既存 workflow 無指定時は補完を起動せず、補助実行の未設定・失敗で既存完了判定を破損させず、必須工程として明示要求された未設定時は黙って除外せず `blocked` とする。
- [ ] 既存 `owner_verifiers` のトップレベル `artifact_ref`・canonical JSON 本文・hash 契約と整合し、複数入力対象の全件完了・実 provider readback・取得完全性・必須引継ぎ成立を検証する。
- [ ] 本文だけでなく metadata・ログ・Git 履歴・評価データへの機密情報・個人情報混入を防止でき、既存単体実行・変更伝播・再開経路が回帰しない。

### 13.3 効率・構成比較評価（既存 `workflow_efficiency.py` 互換＋横断継続利用の補助評価）

既存の `workflow_efficiency.py`（`qa-workflow-efficiency-v1`：2群比較 `baseline` / `candidate`、必須5シナリオ、各群最低2回独立試行）の schema を壊さず、**2群比較の組み合わせ**（`導入前 vs 1スキル`、`導入前 vs 2スキル`、`1スキル vs 2スキル`）で比較する。複数機能・複数 workflow 間の**横断継続利用シナリオは既存5シナリオとは別の補助評価として実施**し、比較対象ごとに利用可能な初期情報（元成果物・過去回答・対象機能）を揃えて、情報の発見・再利用方法の差のみを公平に測定する。

| 評価指標                                                                                                                    | 測定前に固定する採用判断基準                                                                                                                                                                                      |
| :-------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 未承認仮説の誤採用 / 必要質問の誤省略 / 機密漏えい・認可違反                                                                | **0件（絶対条件・1件でも不合格）**                                                                                                                                                                                |
| 抽出漏れ・法則性/差異条件抽出精度・反例検出精度（Semantic評価）                                                             | 同一評価セットで導入前より改善し、2スキル構成が1スキル構成と同等以上であること                                                                                                                                    |
| 重複質問数（補助評価）                                                                                                      | 必要質問を維持したうえで蓄積後の QA における重複質問が削減されること                                                                                                                                              |
| 1ターン最大入力トークン・総トークン・**処理時間（`wall_seconds`）・`request_count`・`skill_call_count`・`reanalyze_count`** | 1ターン負荷と workflow 全体負荷（トークン＋処理時間＋起動回数）を分けて評価し、実装Planで baseline 計測値に基づき固定する許容上限内であれば2スキルを本採用。総負荷・処理時間が上限を超える場合は1スキルへ統合する |

---

## 14. 実装Planへの引き継ぎ事項（基本設計クローズ）

本ドキュメントをもって基本設計を確定とし、次フェーズの**実装Plan**で以下を順に確定・着手します。

| 確定タイミング                       | 対象項目                                                                              | 内容・確認事項                                                                                                                                                                                                                                                                   |
| :----------------------------------- | :------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **実装着手前の必須確認（着手条件）** | **外部入力・信頼境界の実確認** | ハーネス/保存層で許可root・権限/失効・条件付き保存・履歴・独立readbackの接続を確認。未確認なら正式保存・副作用・依存完了を局所blockする。 |
| **実装Planで確定** | 指定ディレクトリの相対配置・identity・既存owner冪等照合 | `<kind>/<identity>.json`、root内の識別、既存owner側の実一意性保証、依存revisionとreadback。案件管理・ブランチ管理・Provider選択をSkillから除外。 |
| **実装時に確定してよい詳細**         | production helper のファイル名・関数分割・JSON Schema 詳細型定義・テスト/fixture 配置 | 既存リポジトリの規約に沿って実装時に決定。                                                                                                                                                                                                                                       |
| **比較評価時に最終決定**             | 新規1スキル vs 新規2スキルの最終選定・性能最適化                                      | 第13.3節の実測結果に基づき確定。                                                                                                                                                                                                                                                 |

---

## 付録：その他の不足専門スキル領域の整理（別課題として分離）

| 領域                              | 現行の対応状況                                                                                                                     | 今後の調査・検討方針                                                                                                                                     | 検討優先度     |
| :-------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------- |
| **セキュリティテスト**            | 汎用設計・非E2E実装/実行で一部対応可                                                                                               | 認証・認可、テナント分離、入力検証、業務ロジック悪用、実行時の安全制約について既存との差分を調査                                                         | 高             |
| **性能・負荷テスト**              | `usability-inspection` のブラウザ計測に加え、`testware-implementation` / `testware-execution` で非機能 testware の実装・実行が可能 | 既存の汎用実行能力と切り分け、負荷モデル・スループット・パーセンタイル・資源使用率・長時間稼働など性能・負荷テスト固有の設計・測定・分析能力の不足を調査 | 高             |
| **API・コントラクト・結合テスト** | `testware-implementation` / `testware-execution` で基礎対応済み                                                                    | OpenAPI契約検証、コンシューマー駆動契約、サービス間結合について既存非E2Eスキルとの境界を確認                                                             | 中〜高         |
| **障害トリアージ・バグ報告**      | `defect-management` および結果分析スキルが既に存在                                                                                 | 新設ではなく、再現条件の最小化・原因切り分け品質を既存スキルの拡張で補えるか確認                                                                         | 低（既存拡張） |
