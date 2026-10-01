# UIテスト対象分析プロファイル: scope / responsibilities

親Plan:
2026-10-01_201500_ui-test-target-analysis-profile.md

この文書は、今回追加する「UIテスト対象分析プロファイル」の責務境界を正本とします。

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

この追加責務はAuthority ownerを増やさず、spec-analysis内の条件付きprofileとして実現します。

AIエージェントからの利用方法は既存のAgent Skills構造をそのまま使い、今回のための製品固有integrationやbootstrap機構は追加しません。

## 2. 責務表

| 内容 | owner | 今回の変更 |
| --- | --- | --- |
| 現在有効な仕様根拠 | spec-analysis | 既存維持 |
| SPEC / DECISION / INFERENCE / UNKNOWN分類 | spec-analysis | 既存維持 |
| UI構造の仕様上の分類 | spec-analysis | profileへ追加 |
| 複数Markdown仕様理解package | spec-analysis | profileへ追加 |
| canonical仕様モデル / Current Effective Authority / Machine Entity | spec-analysis | 既存契約を維持し、package内の単一正本へ配置 |
| 不明点のブロック分類 | question-analysis | 既存維持 |
| 回答のSPEC / DECISION / ASM正規化 | question-analysis | 安定UNKNOWN参照を補強 |
| packageへの回答反映 | spec-analysis | question-analysisの正規化結果を入力に更新 |
| 生きた実画面のcurrent観測 | test-target-inspection | 変更なし |
| repositoryのコード事実 | spec-analysisの補助入力、必要に応じe2e-test-inspection等 | Authorityへ自動昇格しない |
| プロダクトリスク / テスト重点 | test-analysis | 対象外 |
| テスト要求 / 条件 / ケース | 各既存設計Skill | 対象外 |
| workflow開始 / 再開 / 変更伝播 | qa-workflow | profile routingのみ追加 |

## 3. profileを使う条件

profileの選択は「Markdownを要求されたか」ではなく、成果物の目的で判断します。

### profileを使う

次のいずれかに該当する場合:

- テスト設計前の対象理解を、後続工程や別セッションでも再利用する継続成果物として残す
- 仕様書、Figma、Q&A、repository等の複数資料を統合し、画面・状態・業務ルール・不明点を追跡可能に管理する
- PAGE / STATE / VIEW / MODAL等のUI構造を正規化し、今後のテスト分析の入力にする
- 既存のUIテスト対象分析packageを更新 / version upする
- 「テスト対象分析」「対象理解を固める」等、テスト設計前の対象モデル作成が要求の中心である
- テスト観点 / ケースへ進む前に対象理解だけを確定して止める

### 通常spec-analysisを使う

次の場合は既存 `assets/output-template.md` を使い、profileを強制しません。

- 一回限りの仕様要約
- Authority競合の解消だけが目的
- 単一表で十分な小規模仕様整理
- SPEC / DECISION / INFERENCE / UNKNOWN分類だけで要求を満たせる

profile選択を「Markdown」「複数ファイル」等の単語一致だけで決めません。

## 4. canonical仕様モデルと構造化ビュー

UIテスト対象分析packageでも、既存spec-analysisのcanonical contractを維持します。

- canonical正本: `09_authority_and_traceability.md`
- 既存 `assets/output-template.md` と同じ意味契約で、SRC / 分析項目 / Current Effective Authority / Machine Entityを保持する
- 他のpackage fileはcanonical item IDを参照する構造化ビューであり、SPEC / DECISION / INFERENCE / UNKNOWNの別正本を作らない
- 業務ルール、UI構造、入力制約等を人間向けに再配置しても、期待挙動のAuthorityは09へ戻れる
- Current Effective AuthorityからMachine Entityを生成する既存 `authority_entities.py` 契約を維持する
- package固有のversion / manifestはAuthority Machine Entityのidentityやfingerprintを置換しない

## 5. UI構造の正規分類

profileでは次の意味を固定します。

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

routeが同一ならPAGEとは分離します。

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

## 6. 仕様と実装の分離

次を必須ルールとします。

1. 仕様資料、正式決定、承認済みASMを期待挙動のAuthorityとして扱う
2. repositoryや実画面は既存契約どおり補助証拠
3. repositoryで仕様と異なる挙動を見つけても、仕様本文を実装に合わせて書き換えない
4. 差分はimplementation status / spec-implementation gapとして分離する
5. 未実装は「仕様不明」ではなく「仕様は定義済み・実装未確認 / 未実装」と区別する
6. repositoryだけでは決められない仕様を「コード上こうなので仕様もこう」と確定しない
7. 案件コンテキストが実装をAuthorityと明示した場合だけ、既存Authority解決契約に従って扱う

## 7. 不明点の扱い

profile内の仕様UNKNOWNはspec-analysisの安定IDとしてUNK-xxxを使います。

question-analysisは必要なら質問単位のIDを持てますが、同じ論点を再採番せず、元のUNK-xxxとの対応を保持します。

回答後:

- Authority資料更新 → SPEC
- 正式なステークホルダー決定 → DECISION
- 暫定前提 → 承認済みASM
- 回答が不明 / 判断不能 → UNKNOWN継続

解消したUNKはcurrent unknown一覧から外しますが、回答反映済み履歴またはchangelogから追跡可能にします。

「一度回答があるが暫定だった論点」を再確認する場合も、同じUNK IDを使います。

## 8. packageとtest-target-inspectionの関係

profile packageは「仕様上どうあるべきか」を中心にします。

test-target-inspection成果物は「現在の実対象で何を観測したか」です。

profileからcurrent実対象確認が必要になった場合:

1. qa-workflowがtest-target-inspectionへrouting
2. 観測結果を観測事実として取得
3. 観測結果をspec-analysisへ補助入力として戻す
4. 仕様と一致 / 不一致 / 仕様未定義を区別
5. 観測事実だけでSPEC / DECISIONへ昇格しない

## 9. 進行モード

既存qa-workflowのcontinuous / gatedをそのまま使います。

今回のように「まず理解を説明して確認後にファイル化」「1手順ずつ合意する」と明示された場合はgatedで扱います。

gatedの場合:

- spec-analysis package draftまたは理解説明を提示
- ユーザー承認前にtest-analysisへ進まない
- question-analysis回答待ちでもブロッカーでない範囲はpackage更新可能
- 次工程はユーザー承認後のみ

## 10. 対象外となる誤った統合

次は実装しません。

- test-target-inspectionをspec-analysisへ吸収する
- repository実装をデフォルトAuthorityにする
- profileを全spec-analysis requestで強制する
- test-analysisのリスク評価をprofileへ複製する
- test-condition-designのテスト技法をprofileへ先回りする
- coverage-analysisを使わずprofile独自にテストカバレッジを判定する
- 任意形式文書を統合する汎用document engineを作る
