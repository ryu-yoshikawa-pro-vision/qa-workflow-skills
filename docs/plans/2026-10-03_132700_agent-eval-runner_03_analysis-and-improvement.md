# 実Agent評価結果の自動分析・Skill修正・再評価Plan

この文書は[親Plan](./2026-10-03_132700_agent-eval-runner.md)のフェーズ1・フェーズ2に追加する改善工程の実装契約です。対象repo固有の評価仕様は[フェーズ2Plan](./2026-10-03_132700_agent-eval-runner_02_qa-training-store-integration-eval.md)を正本とします。既存の評価ランナー・grader・隔離・比較条件を維持して実装します。

## 目的と完了条件

実Agent評価の保存結果から、Agentが問題を分析して根拠を記録し、十分な根拠があるSkill起因の問題だけを隔離環境で修正・再評価します。原因を確定できないもの、変更リスクが高いもの、再評価で改善が確認できないものは**レビュー待ち**として、必要な判断・証拠・候補差分とともに保存します。

1回の実行だけで無制限に自動修正を続ける仕組みにはしません。自動修正による採用・PR作成・push・mergeは行いません。人間は検証済みの修正候補とレビュー待ちを確認し、採用を決めます。

対象は明示したSkill利用時の成果物品質および固定workflow評価です。native `description` trigger評価やSkillの自動発火最適化は対象外です。

## 入力と責任分担

- 入力は既存ランナーが保存した`result.json`、ケース別`grade.json`、安全化された成果物・失敗根拠・provenance・既存検査結果です。データ欠落・改ざん・検証不能は推測で補いません。
- **既存grader / Evaluator**: 正規の品質判定、固定Reference・rubric・expectedの管理、評価条件の整合確認、修正前後の再評価を担当します。Judgeを独立検証した結果の正本は[Judge評価・改善Plan](./2026-10-03_132700_agent-eval-runner_04_judge-evaluation-and-improvement.md)に従います。比較する2 revisionは同一の固定Evaluatorで採点します。
- **分析Agent**: 評価結果・成果物・公開可能なSkill sourceの根拠から問題を分類し、原因仮説と対象箇所・修正方針を記録します。Agentの説明や自称の確信度は事実や合否の根拠になりません。
- **修正Agent**: 下記の自動修正条件を全て満たした案件だけ、隔離した候補Skill作業領域で最小差分を作ります。Agent subprocessの実行には既存`executor.py`を再利用し、特定SDKへの依存は追加しません。
- **改善実行の制御**: 既存ランナー結果の検証、機械的な修正可否判定、許可path検査、テスト、再評価、保存を担当します。LLM自身に許可判定を一任しません。
- **人間**: レビュー待ちの解決、検証済み候補の採用、既存branchへの取り込みを担当します。修正Agentから採用権限を取りません。

分析Agent・修正Agentに、評価用`expected.json`、`reference.md`、採点rubric本文、Judge設定、Evaluator内部コード、認証情報、元の汚染されていない固定targetを渡しません。Evaluatorが生成する**必要最小限の安全化された判定結果・根拠抜粋**のみを渡します。Agentが評価基準そのものを書き換えて合格を作ることを禁止します。

## 実行工程

```text
既存の実Agent評価（固定Evaluatorで採点）
  ↓
Judgeの独立検証状態を照合
  ├─ 未検証・不一致 → Judgeレビュー待ち（Skillは自動修正しない）
  └─ 検証済み → 失敗・needs_review・証拠不足を収集
  ↓
分析Agentによる原因仮説・根拠の整理
  ↓
機械的な自動修正条件を照合
  ├─ 条件不足・判断不能・高リスク → レビュー待ちへ保存
  └─ 全条件成立 → 隔離したSkill候補を修正
                         ↓
                    許可pathと差分・関連テストの検証
                         ↓
                    固定Evaluator・同条件で再評価
                         ↓
                    根拠付きで変更前後を比較
                         ├─ 改善を確認 → 検証済み修正候補として保存
                         └─ 未改善・悪化・判定不能 → レビュー待ちへ保存
```

実行環境またはEvaluatorの障害はSkillの欠陥として修正対象にせず、診断根拠を保持してレビュー待ちにします。既存の`execution error`・`evidence_unverified`・`evaluator_incompatible`等の元の状態を保持します。

## 自動分析

分析は既存graderのcriterion別結果・失敗根拠・生成成果物・変更対象Skillの該当箇所と、比較可能性・使用証拠を突き合わせます。

各案件に、少なくとも次を記録します。

- 元run / attempt / eval IDまたはscenario ID、固定Evaluatorと候補Skill revision・実行条件の識別子
- 失敗したcriterion・機械判定、原成果物path、根拠の引用箇所・該当Skill path
- 問題の分類（Skillの指示・実装、Agentの一時的な失敗、Evaluator / Judge、評価入力・target仕様、実行環境、証拠不足、判断不能）
- Skill起因と判断する根拠、他の原因を除外できるか、同条件での再現結果
- 最小修正案、影響を受ける既存契約・テスト、判断不能事項、取るべき確認手順
- 自動修正可否と**成立・不成立の条件ごとの根拠**

出力は`analysis.json`と読みやすい`analysis.md`で保存します。根拠となる元ファイルの内容hashとpathを参照し、元の判定結果・証拠は変更しません。判断できない原因をSkillの不具合として断定しません。

## 自動修正を許可する条件

次の**全条件**について、機械的に確認できる実行・再現性・許可pathの事実と、分析Agentが根拠を示した原因仮説を突き合わせます。原因をSkillに帰属する意味判断は完全に機械的な事実として証明できないため、参照先の根拠が不明確な場合や代替原因を除外できない場合はレビュー待ちにします。LLMが出す「確信度80%」等の数値や、根拠のない自己申告だけで修正を許可しません。

1. 固定Evaluatorの評価が実行エラーなく成立し、比較に必要な実行profile・隔離条件・provenanceが確認済みである。**判定に使用するcriterionは確認済み正解データによるJudge独立検証が成立し、重要な誤判定・判定揺れ・検証不足がない**。検証済み範囲とJudge / 正解データrevisionがrunに紐付く。
2. 同じSkill revision・評価caseを独立に2attempt以上実行し、問題が再現している。単発のJudge判定や互いに矛盾する証拠だけでは許可しない。
3. 失敗のcriterion / 機械判定と成果物の具体的な違反箇所が特定でき、根拠を対象Skillの特定の指示・実装箇所へ対応付けられる。
4. Evaluator・Judge・target仕様・実行環境・証拠収集に異常がないことを検証済み結果で確認し、問題の原因を1 Skillへ絞る具体的な根拠がある。これらの代替原因を除外できない場合や、原因候補が複数ある場合は許可しない。
5. 修正対象は**1つのSkill package**に限定でき、変更対象path・回帰テスト・受入criteriaを事前に列挙できる。複数Skillや共通契約の変更が必要な場合はレビュー待ちにする。
6. 変更はそのSkillの`SKILL.md`、`references/**`、`scripts/**`、`assets/**`内に限定でき、関連テストと既存の検証手順を実行できる。対象pathと操作は許可リストで検査し、Agentが許可範囲外へ書き込めないよう隔離する。
7. 評価基準の緩和、検査の無効化、証拠の捏造、既存のセキュリティ・データ保護・traceability・runtime契約の弱体化を伴わない。

上記の判定ができない、対象が複数、品質判断が揺れる、既存仕様が不明、破壊的変更・権限拡張・依存関係追加が必要なケースはレビュー待ちに回します。例外的な自動許可や、新たなLLM信頼度スコアは設けません。

## 自動修正と再評価

- 修正は元のEvaluator checkout・ユーザーの作業ツリー・固定targetとは別の**使い捨て作業領域**で行います。元branchへの書込み・push・PR作成を行いません。
- Judgeの改善が必要な場合はSkillの修正を停止し、Judge改善候補の作成・独立検証・レビュー待ちへ回す。Judgeを改訂する際は固定Evaluatorを切り替え、Skillの旧・新revisionを双方再評価する。基準とSkillを同時に変更して改善と結論付けない。
- 候補の通常Skill packageだけを編集可能とし、Evaluator・rubric・dataset・評価結果・固定target・設定を読み取り専用または非公開にします。環境境界の確認に失敗したら修正を開始しません。
- Agentが差分を作った後に、許可path、対象Skillの単一性、不正なリンク・ファイル境界、既存契約の検証結果を確認します。意味上の契約後退を機械検証だけで否定できない場合はレビュー待ちにします。違反した候補の差分は元branchに反映せず、診断情報を保存します。
- 同じ候補に対する自動修正は**1回**とし、無限修正ループを作りません。Agent timeout・最大変更範囲・使用する実行profileはrun開始時に固定します。修正失敗時の繰返しはユーザーが別runとして明示的に起動します。
- 必要な関連Skillテスト、既存deterministic / semantic / runtime検査、ポータビリティ確認を行います。必要な検証を実行できない場合は自動改善済みにしません。
- 候補SkillのGit revisionとfile hashを独立して固定した後、**元の固定Evaluator・target・入力・Agent / Judge profile・隔離条件**でbaseline / candidateを各2attempt以上評価します。必要なSkill使用証拠がない場合、Skill修正が原因の改善とは断定しません。
- 重要なcriterionまたは機械品質に一貫した実質的な改善があり、他の重要観点・既存契約の回帰がなく、比較条件が揃い、上記検証が全て成立する場合だけ、候補を検証済みとします。修正Agentの「直った」という説明だけでは判断しません。
- 評価基準を変える必要が出た場合は修正候補を自動採用しません。固定Evaluatorを改訂するかはレビュー待ちとし、必要なら両Skill revisionを新Evaluatorで改めて評価します。
- 候補は再現可能なpatch・候補revision・テスト結果・比較結果とともに保存し、元のbaselineを変更しません。検証済みでもmain / PRへ自動取り込みません。

## レビュー待ちの保存契約

`--output-root`配下の`improvement/`に次を保存します。

```text
improvement/
  analysis.json
  analysis.md
  candidates/       # 再評価で改善を確認した修正候補と根拠
  review-pending/    # 原因不明・低確度・検証失敗・高リスクの案件
  result.json        # 修正実行・検証・分類の結果（元runとは別）
```

各レビュー待ちには、元runへの参照、確認済み事実、判断できなかった事項、止めた条件、根拠file、次に人間が判断する内容、候補patchがある場合はその保存先を記録します。未完了をPASSとして集計しません。同じ評価失敗から同じレビュー案件を重複作成しないため、元run・case・criterion・Skill revisionから安定した識別子を生成します。削除やcloseの自動処理、外部Issue / PRへの自動書込みはしません。

## CLI・処理境界

- 既存`run.py`は実Agent生成・採点・収集を担当し、既存graderを変更しません。
- 新規`scripts/skills/evals/agent/improve.py`は保存済みrunを入力として、分析・修正可否判定・隔離修正・テスト・既存ランナーによる再評価・保存を順に実行します。
- `--analyze-only`で修正せず分析結果・レビュー待ちだけを保存できるようにします。
- `--analysis-command`と`--repair-command`は外部argvとして注入し、既存`executor.py`でtimeout・子孫process終了・stderr安全化を扱います。Agent用の非秘密実効profileと隔離の検証は評価runと独立して記録します。
- 各runは明示指定された対象caseのみ処理します。`--skill all`の評価結果から暗黙に全件修正を開始しません。無条件の繰返し起動・夜間実行・常時CIでのLLM呼出しは行いません。
- 対象候補がない場合も分析結果・レビュー待ち件数・停止理由を保存し、正常終了と「改善済み」を区別します。

追加するのは`improve.py`と分析結果・レビュー待ちの保存に必要な最小の部品・テストだけです。新しいAgent runtime、汎用workflow framework、DB、独自スコア式、Agent SDK・MCP専用実装は追加しません。

## テストと受入検証

通常CIではfake Agent / fake Judgeで、次を検証します。

- 確認済みの単一Skill原因・再現性あり・関連テスト実施可能なケースだけ修正に進む
- 判断不能・根拠不足・Judge揺れ・未検証criterion・Judge正解データ不足・非互換・実行環境エラー・複数Skill原因・仕様不明では修正せずレビュー待ちへ入る
- 分析Agentが修正可と自己申告しても機械的条件を満たさなければ修正されない
- 変更許可範囲外、Evaluator / expected / rubric / target変更、テスト無効化・基準緩和は拒否する
- 修正Agentのtimeout・異常終了・許可外差分でも元Evaluator・target・作業ツリーを変更しない
- 候補のテスト失敗、再評価未改善、回帰、結果の揺れ、使用証拠不足は改善済みにせずレビュー待ちに残す
- 全条件成立時はpatch・候補revision・関連テスト・baseline / candidateのrepeat比較が保存され、元runが不変
- `--analyze-only`は実ファイルを書き換えず分析・レビュー待ちだけ生成する
- native trigger・自動push / PR・merge・外部LLM CIは実行されない

実Codex smokeでは、実際の評価結果から分析のみの経路と、**確認済みのSkill起因問題1件に対する自動修正・同条件の再評価**まで実行します。適格な実問題を特定できず自動修正できなかった場合は、分析・振分け機能の成立と自動改善実証の未達を別々に報告します。合格させるための人工的なbaseline劣化やJudge基準緩和は行いません。
