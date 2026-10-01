# UIテスト対象分析プロファイル: spec-analysis package

親Plan:
2026-10-01_201500_ui-test-target-analysis-profile.md

責務境界:
2026-10-01_201500_ui-test-target-analysis-profile_01_scope-and-responsibilities.md

この文書はspec-analysisへ追加するUIテスト対象分析packageの構造と更新契約を正本とします。

## 1. 変更対象

### 既存変更

- skills/spec-analysis/SKILL.md
- skills/spec-analysis/references/guidance.md

### 新規

- skills/spec-analysis/references/ui-test-target-analysis.md
- skills/spec-analysis/assets/ui-test-target-analysis/README.md
- skills/spec-analysis/assets/ui-test-target-analysis/00_scope-and_context.md
- skills/spec-analysis/assets/ui-test-target-analysis/01_ui_structure_and_navigation.md
- skills/spec-analysis/assets/ui-test-target-analysis/02_behavior_and_business_rules.md
- skills/spec-analysis/assets/ui-test-target-analysis/03_fields_and_validation.md
- skills/spec-analysis/assets/ui-test-target-analysis/04_flows_and_data.md
- skills/spec-analysis/assets/ui-test-target-analysis/05_notifications_and_external_interactions.md
- skills/spec-analysis/assets/ui-test-target-analysis/06_spec_inconsistencies_and_pending.md
- skills/spec-analysis/assets/ui-test-target-analysis/07_current_unknowns.md
- skills/spec-analysis/assets/ui-test-target-analysis/08_repository_implementation_status.md
- skills/spec-analysis/assets/ui-test-target-analysis/09_authority_and_traceability.md
- skills/spec-analysis/assets/ui-test-target-analysis/CHANGELOG.md
- skills/spec-analysis/assets/ui-test-target-analysis/MANIFEST.md

ファイル数を増やすこと自体を目的にしません。required coreとoptional domain fileを明確に分けます。

### required core

- README.md
- 00_scope_and_context.md
- 01_ui_structure_and_navigation.md
- 02_behavior_and_business_rules.md
- 06_spec_inconsistencies_and_pending.md
- 07_current_unknowns.md
- 09_authority_and_traceability.md
- CHANGELOG.md
- MANIFEST.md

### optional

対象仕様が存在する場合だけ含めます。

- 03_fields_and_validation.md
- 04_flows_and_data.md
- 05_notifications_and_external_interactions.md
- 08_repository_implementation_status.md
- 案件固有domain file

optional fileを空ファイルとして作りません。含めないfileはMANIFESTへ登録せず、READMEには必要な場合だけ「対象外 / 不使用」として説明します。

## 2. SKILL.mdの変更

SKILL.mdには次だけを追加します。

- テスト設計前の対象理解を継続成果物として残す場合、複数資料からUI構造・業務ルール・不明点を追跡可能に整理する場合、または既存UI target packageを更新する場合は `references/ui-test-target-analysis.md` を読む。単なるMarkdown出力要求だけではprofileを選ばない
- 通常の仕様分析では既存assets/output-template.mdを維持する
- profile利用時もSPEC / DECISION / INFERENCE / UNKNOWN、Authority解決、停止条件は既存契約を正本とする
- test requirement / condition / caseへ先回りしない
- packageを更新する場合は既存versionを入力として扱い、現在版の完全packageを生成する

詳細なPAGE分類やfile contractはSKILL.mdへ複製せずreferenceを正本とします。

## 3. ui-test-target-analysis.md

このreferenceに次を定義します。

### 起動条件

- テスト設計前の対象理解
- 複数資料統合
- UI画面 / modal / state構造整理
- 継続更新するMarkdown package
- 既存packageのrevision

### 情報源

既存spec-analysisのAuthority contractを再利用し、profile固有に新しい優先順位を作りません。

案件固有優先順位がある場合はそれを使用します。

### canonical Authority / traceability

profile packageでも既存 `assets/output-template.md` のcanonical契約を維持します。

- `09_authority_and_traceability.md` は既存output-templateの以下を正本として保持する
  - 情報源 / 正本参照一覧
  - 分析項目
  - 現在有効な仕様根拠
  - 後続Skillへの補足
  - Machine Entity（機械証拠）
- 業務ルール / 状態 / フロー / 制約は01〜05へ詳細ビューを持てるが、Authority item IDの正本は09
- 01〜08で新たな仕様判断を追加した場合、必ず09のSPEC / DECISION / INFERENCE / UNKNOWNへ閉じる
- 09のCurrent Effective Authorityを既存 `authority_entities.py` の入力へ変換できる状態を維持する
- Machine Entityのfingerprintは既存helperで生成し、テンプレートやAgentが手入力しない
- package version / file hashはMachine Entityのcontent fingerprintとは別物

### 正規UI分類

- PAGE
- STATE
- VIEW / STEP
- MODAL
- BROWSER-DIALOG
- PANEL / POPOVER / GLOBAL UI
- EXTERNAL
- SHARED PAGE

### package分割

1ファイルへ巨大な仕様を詰め込まず、責務単位で分割します。

固定ファイルは「保存場所」であり、新しいAuthority layerではありません。

各仕様項目のstable IDとsource refを保持し、同じ仕様を複数ファイルへコピーする場合は正本箇所と参照箇所を明確にします。

### 案件固有追加ファイル

次のような大きいdomainがある場合は追加ファイルを許可します。

- CSV / export
- email template
- notification
- billing
- permission matrix
- external API
- mobile-specific behavior

ただし追加ファイルはREADMEとMANIFESTへ登録し、同じ責務を複数ファイルへ重複させません。

## 4. package各ファイルの責務

### README.md

- package名
- version
- generated / updated date
- 対象
- 利用情報源
- authority方針
- ファイル一覧
- 現在の未解消件数
- 次の工程へ進める範囲 / ブロック中範囲

READMEを詳細仕様の複製場所にしません。

### 00_scope_and_context.md

- 対象機能
- 対象ユーザー / ロール
- 対象画面
- 対象情報源
- 正本 / 優先順位
- 対象外
- 用語
- repository実装確認基準がある場合の基準branch / commit
- 分析上の前提

### 01_ui_structure_and_navigation.md

- PAGE一覧
- path
- VIEW / STEP
- STATEまたは状態軸
- MODAL
- browser dialog
- panel / external / shared UI
- navigation / entry / exit

同一route内のstepを別PAGEへしません。

### 02_behavior_and_business_rules.md

- lifecycle
- business rule
- status transition
- operation rule
- permission behavior
- success / failure behavior

### 03_fields_and_validation.md

- field
- required / optional
- default
- format
- min / max
- boundary
- trim / normalization
- error
- enable / disable condition
- input method等

テスト技法の適用やテストケース化はしません。

### 04_flows_and_data.md

- user / business flow
- process flow
- data display / data originの仕様上の関係
- state transitionに必要なinput / output
- external interactionの入口

DB値やAPI responseをUI期待結果としてテストケース化しません。

### 05_notifications_and_external_interactions.md

該当する場合のみ使用します。

- in-app notification
- email
- export / download
- external documentation
- support / chat
- external destination
- recipient / timing / navigation

### 06_spec_inconsistencies_and_pending.md

- 資料間矛盾
- typoとして解消したもの
- 正式回答で解消したもの
- 未解消のissue
- source conflict
- pending external specification

解消済み履歴を保持しますが、current unknown一覧の正本にはしません。

### 07_current_unknowns.md

currentなUNKNOWNだけを一覧化します。

別節に回答反映済みを残してもよいですが、現在確認対象と解消済みを混ぜません。

各UNKNOWNはstable UNK IDを持ちます。

### 08_repository_implementation_status.md

repository確認を行った場合のみ使用します。

- 基準branch / commit
- 実装確認できた範囲
- 未実装
- 仕様-実装差分
- 実装だけに存在する分岐
- 実装確認不能理由

このファイルの内容を仕様本文へ自動昇格させません。

### 09_authority_and_traceability.md

package全体のcanonical仕様モデル。

既存 `assets/output-template.md` の意味契約を再利用し、最低限次を含みます。

- 情報源 / 正本参照一覧
- SPEC / DECISION / INFERENCE / UNKNOWNの分析項目
- Current Effective Authority
- 各構造化ビューで使用するstable item ID
- 後続Skillへの補足
- Machine Entity

01〜08に記載した期待挙動は、09のstable item IDへ追跡できなければなりません。

### CHANGELOG.md

versionごとの差分と、どのUNKNOWN / issue / decisionを反映したかを記録します。

過去versionの全文を複製しません。

### MANIFEST.md

- package version
- 含まれるファイル一覧
- 任意でhash / source revision

hashを採用する場合はAgentが実際に計算できる環境でのみ生成します。計算できないのに疑似hashを作りません。

## 5. version contract

profileでversioned packageが要求された場合:

1. 初回はv00
2. material updateごとにv01, v02...と1増分
3. 既存packageがvNNなら次はvNN+1
4. 同一versionの部分ファイルだけ差し替えた状態を最終成果物にしない
5. README / CHANGELOG / MANIFESTのversionを一致させる
6. 変更後も全ファイルを含む完全版を出力する
7. 過去versionは履歴でありcurrent仕様の参照前提にしない

ユーザーや案件が別version policyを指定した場合はそちらを優先します。

## 6. 更新契約

回答や新資料が来た場合:

1. 変更されたAuthority / DECISION / ASMを解決
2. 影響するstable item / UNKを特定
3. 09_authority_and_traceability.mdのcanonical modelを更新
4. 09のstable itemを参照する01〜05の構造化ビューを必要な範囲だけ更新
5. 07_current_unknownsの状態を更新
6. 06の矛盾 / pending履歴を必要に応じ更新
7. implementation statusに影響する場合だけ08を更新
8. CHANGELOGへ変更を記録
9. READMEのversion / current unknown件数を更新
10. MANIFESTを更新
11. 09のCurrent Effective AuthorityからMachine Entityを既存helperで再生成できることを確認
12. package全体の整合を確認

同じ回答を複数ファイルへ手動コピーすることを設計目的にしません。各ファイルへ必要な意味だけ反映します。

## 7. 大規模資料の分割規則

次の場合は案件固有ファイルへ分割できます。

- 1 domainが他のfileより明らかに大きい
- notification / email template等で大量のvariantがある
- external API等がUI仕様と別のAuthorityを持つ
- CSV / export等が独立flowを持つ

分割時は:
- ファイル名をdomain責務に合わせる
- README / MANIFESTへ登録
- current unknownの正本は07のまま
- repository statusの正本は08のまま
- canonical Authority / traceabilityの正本は09のまま
- 同じ仕様項目を二重正本にしない

## 8. package品質ゲート

- source由来と推論が混在していない
- PAGEがpath単位である
- 同一route内step / viewを別PAGEへしていない
- MODALとbrowser dialogを分離している
- 直交する状態を無理に排他STATEへしていない
- 実装差分を仕様へ上書きしていない
- current unknownとresolved historyが矛盾しない
- 解消済みUNKNOWNを再質問していない
- versionが全packageで一致する
- READMEのcurrent unknown件数が07と一致する
- CHANGELOGが今回変更を説明できる
- MANIFESTにcurrent packageの全ファイルがあり、省略したoptional fileを存在するものとして列挙していない
- 01〜08の期待挙動が09のstable item IDへ追跡できる
- 09のCurrent Effective Authorityが既存spec-analysisのcanonical schemaを維持している
- Machine Entityが既存 `authority_entities.py` で生成可能で、fingerprintを手入力していない
- test requirement / condition / caseを先回りしていない
- UIで観測不能な内部挙動をUIテスト期待結果として確定していない

## 9. zip / file artifact

Skill contractとしてZIP生成手段を固定しません。

ユーザーが「zipで出力」を要求し、利用中Agentにfile artifact生成能力がある場合は、current versionの全packageを1 archiveへまとめます。

能力がない場合は、同じpackage構造をtext / workspace上で提供し、存在しないdownload linkを捏造しません。
