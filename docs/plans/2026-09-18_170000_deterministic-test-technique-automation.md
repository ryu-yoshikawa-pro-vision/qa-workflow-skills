# テスト分析・テスト技法の決定論的自動化Plan

このPlanは長文化するため、内容を見出し境界で分割しています。レビュー・実装時は以下5ファイルを順に読み、全体を1つのPlanとして扱ってください。

## 対象ブランチ

`feat/deterministic-test-technique-automation`

## 基準

- 基準branch: `main`
- 基準commit: `3510e6ffce87ba8c025ebde22f9947dbb6074f9c`
- 対象リポジトリ: `ryu-yoshikawa-pro-vision/qa-workflow-skills`

## 構成

1. [目的・現状・自動化対象の全体一覧](./2026-09-18_170000_deterministic-test-technique-automation_01_scope-and-inventory.md)
2. [実行時アーキテクチャ・入力出力契約](./2026-09-18_170000_deterministic-test-technique-automation_02_runtime-architecture-and-contracts.md)
3. [各テスト技法のgenerator・検査ロジック](./2026-09-18_170000_deterministic-test-technique-automation_03_generators-and-algorithms.md)
4. [UIパターン・外部標準・既存プロジェクトの扱い](./2026-09-18_170000_deterministic-test-technique-automation_04_ui-patterns-and-external-references.md)
5. [評価・CI・実装順序・完了条件](./2026-09-18_170000_deterministic-test-technique-automation_05_evaluation-ci-implementation-order.md)

## このPlanの基本方針

自然言語の仕様、Figma、Q&A、実装等から「何が条件・境界・状態・因子・制約・期待結果の根拠になるか」を判断する処理はLLMに残します。

あわせて、調査でテスト分析・設計に必要と判断したDomain Testing、CRUD Testing、Random Testing、Metamorphic Testing、Syntax-Based Testing等を、既存の`test-analysis` / `test-condition-design`の責務を崩さず正式なSkill契約へ追加します。新しいSkillは作りません。runtime scriptは既存6 Skillへ追加し、`qa-workflow`ではstale・完了判定等の機械処理だけをscriptへ分離します。`spec-analysis`にはruntimeを追加せず、下流fingerprintの正本となるAuthorityのcanonical machine JSONを成果物へ追加します。

一方、構造化済みの入力から一意または機械的に導出できる次の処理は、可能な限りSkill内のscriptへ移します。

- 値・組合せ・ルール・遷移・経路の列挙
- 成立不能条件の判定とCoverage母集団からの除外。候補と根拠は保持する
- カバレッジ計算
- 欠落・重複・矛盾・到達不能の検出
- 確定済み数値からのリスクレベル算出
- 変更済み要素からの構造的な影響範囲抽出
- Authority / Risk → TR → TCN → CI → TCの構造的な閉鎖・優先度継承
- 追跡グラフの閉鎖性・孤立確認
- UI要素種別から一般的な確認候補を引く処理

このPlanでいう決定論性は、**同じcanonicalなruntime入力、同じ上流Entity content fingerprint、同じruntime / generator contract version、同じruntime / generator implementation fingerprint、同じ静的参照データversionから同じgenerator結果を得ること**です。runtime入力には正規化済みモデルと技法選択元を含め、実際に消費したAuthority / Risk / TR等はcanonical machine Entityのcontent fingerprintとしてgeneration条件へ含めます。既存CI ID等を維持するstateful処理は、これらに加えて同じtarget annotation / Disposition / merge指定と、同じprevious target / CI / expected result root / ID stateを入力した場合に同じ結果を得ることを保証します。自然言語資料から正規化済みモデルを作るLLM判断まで「同じ入力なら常に同じ結果」と保証するものではありません。正規化の意味妥当性・漏れはsemantic evalと既存の上流閉鎖で確認します。

正規化済みモデルと各担当Skillが保存するcanonical machine Entityを意味上の正本とし、Machine Entityは`(skill, entity_type, entity_ref)`で識別します。Coverage表、生成組合せ、Coverage Item等の機械生成部分は派生成果物として扱います。既存成果物を再利用する場合も、runtime対象unitは現在のcanonical machine Entityと正規化済み入力からscriptを再実行し、保存済みruntime resultを現在世代の実行cacheとして扱いません。上流Authority、直接依存する上流runtime結果、正規化済みモデル、runtime / generator contract、runtime / generator実装、静的参照データのいずれかが変わった場合は、fingerprint比較で影響する派生成果物だけをstaleとして`要再検証`へ戻し、再生成・再検証が完了するまで完了扱いしません。

scriptは仕様根拠や業務ルールを創作しません。`technique_slug`はSkill上の正規テスト技法だけを表し、内部model / adapterは別の`model_type`で識別します。技法選択元は`selection_source / selection_key`で正規技法modelへ追跡し、再利用か新規かは`identity_action`で別に管理します。runtime generatorへ移さないエラー推測のCoverage Itemも、既存の意味判断を維持したままCI Machine Entityへ載せ、traceabilityとstale判定の対象にします。CI化するmachine Coverage targetはgenerator別に固定した実行可能`execution`を持たせます。partial / unsupportedはclosure行が存在するだけで完了扱いせず、既存Skillで許可された扱いまたはcurrentなfallback先へ妥当に閉じていることを検査します。最終完了判定ではdispatch表から導出した期待runtime unit集合と、各Skill validatorが導出した期待Machine Entity集合を実際の集合と比較し、丸ごと欠落したunit / Entityを見逃しません。

期待結果が現在有効な仕様根拠へ追跡できない場合は、生成結果を完成済みテストとして扱わず、既存の停止条件・ブロック中・質問ルーティングへ戻します。
