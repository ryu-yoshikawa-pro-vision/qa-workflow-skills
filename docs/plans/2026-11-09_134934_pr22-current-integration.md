# PR #22 現在の統合・最終受入計画

## 目的

PR #22を、既存の開発連動QA Plan、QA全工程Plan、詳細01〜08、統合管理READMEの受入契約に従って統合する。既存の15＋10完了条件、S1〜S17、人間編集8ケース、5つの効率比較シナリオを変更・省略しない。この計画は実行順と現状を記録し、既存Planの代替にしない。

## 現在の状態と根拠

2026-11-13時点でPR #22はopen、base `main`。担当PR #23〜#32（A〜J）と#34は`feat/development-qa-traceability`へsquash統合済み。統合HEAD `21cbdc5a`ではValidate Agent Skillsだけが失敗していた（READMEの7 Skill未登録）。この失敗は共有登録とqa-workflow routingの修正で解消した。

その後、利用者が決定した保存先（qa-training-storeの専用branch `qa/artifacts`）・承認方式（対話での同意＋認証済みpush＋activity API）・外部Issue（案件ごとにProject Contextで設定、未設定は対象外）・製品CI（保存先branchのref参照）に従い、担当間の接続6経路、owner verifier登録、実Git providerと製品CIの受入、実runner、意味評価の再実行、trigger runnerを実施した。条件ごとの判定、証拠、残件は[最終受入の検証記録](../implementation/pr22/evidence/final-acceptance-2026-11-12/README.md)を正本とする。

総合判定は**未完了**。利用者の承認（2026-11-13）により、次を対象外とし、阻害要因に含めない：API-only・batch・非機能・直接TCのrunner経路、releaseを含む通し・実Q06の配置合意・外部Issue管理先の設定、Codexでの受入、Windows実行、効率比較の人間のレビュー・承認時間。対象外を除いて残る主要な未達事項は、trigger評価の不合格（肯定8・否定1 query）、効率比較の未実証（品質・安全がpassでない試行、token・費用の悪化、補助scriptの書込み先）、F 3 Skillの実成果物での検証と承認の真正性（検証入口は2026-11-14に実装・登録済み。完了不可のまま）の3項目である。これは個別受入条件のすべてではなく、対象外承認を受けていない未実施・部分・blocked条件が§8の詳細表に残る（残件の正本は最終受入の検証記録§8）。意味評価は評価入力の補完で11件passし、停止条件はSkillを変えず現状維持とする。

## 統合時に確認した文書・コード差異

PR #24の担当記録ではProject ContextテンプレートSection 12/13の区切り行が2本とされ、parserの3本以上という条件との差が報告されている。PR #22の現行treeではテンプレートが既に3本以上へ修正され、`project_context_ids.py`によるcreate入力検証で`valid=true`を確認した。2本の行は古いC作業treeで再現した状態で、今回PR #22の現行テンプレートに変更は不要。再発を防ぐため、`tests/skills/runtime/test_project_context_ids.py`にrepository既定テンプレートを実parserへ渡す回帰テストを追加済み。PR #22 head `591dcb2`のDeterministic Output Evalsでもこの回帰テストを含むsuiteはsuccess。

PR #25 Cの実装ではUI構造分析と期待仕様Authorityが別ownerだが、共有README、`qa-workflow`、`guidance.md`は以前`spec-analysis`のUI target modeにUI package作成まで割り当てていた。共有契約を更新し、UI構造・操作・状態・遷移・human editingと`ui-target-v1`履歴／migrationは`ui-target-analysis`、期待仕様・Authority・US / UC / Behavior / AC / UNKNOWNは`spec-analysis`と明記した。D / Gの独立Skill追加もREADME catalog、trigger / semantic index、routingへ反映した。

## 既存契約

- 最終統合先はPR #22の`feat/development-qa-traceability`。担当の独立実装は各owner PR、親PRは取り込み・接続・横断検証・最終判定を行う。
- 共有runtime・README・EVALS・CIの実装ownerはA。UI構造分析とhuman editingはCの`ui-target-analysis`、期待仕様Authorityは`spec-analysis`。既存writer・validator・runtime・共通helperを再利用し、担当所有外の正本を親PRへ複製しない。
- 各担当の局所PASSは親PRの完了を意味しない。実際に保存された各owner正本・ID・revision・承認・readback・runner結果を使う。
- 案件provider、認証済み承認者、実案件Q06、製品CIの受渡し方式が未確定・未接続なら該当受入をblockedにする。fixtureやCI成功で代替しない。
- 最終merge／close、force push、branch削除はこの計画の対象外。

## 範囲

### 含む

- Readyかつ担当完了根拠が揃ったowner実装のPR #22 branchへの取り込みと競合解消。
- A ownerの共有routing、README catalog、EVALS、共通CI契約を、C〜Jの実装を含む現状へ同期するための引継ぎ・統合確認。
- B→C/D→E、F/G/H/I→Jの実際の成果物ID／revisionによる横断接続、consumer・migration・履歴互換の確認。
- 15＋10条件、詳細01〜08、S1〜S17、人間編集8ケース、詳細07の5シナリオ、全CIの証拠整理と最終判定。

### 含まない

- E/F/H/I/Jの担当実装をPR #22に重複実装すること。未完成owner範囲はそのPRの完了までblockedとして残す。
- 根拠がない案件provider・保存先・認証者・CI受渡し方式の決定、実案件データの捏造、外部書込み。
- PR #22をmainへmergeすること、close／release、force push、branch削除。

## リスク・未確定条件

- 横断接続の多くはowner間のスキーマ決定を要する（B→D、D→E、E2E選定→下流、I→J、G/H/I→J）。PR #22で一方的に決めず、各owner契約の改訂として扱う。
- provider、権限者、実案件データ、製品CI接続が無い条件は、権威ある入力が揃うまでblocked。
- 長時間trigger評価は利用者の停止指示を維持している。利用者の承認後にrepo管理のrunnerで新14 Skillの部分評価を実施した（結果は最終受入の検証記録7.2）。

## 実施順序

1. PR #22 head・working tree・CIを固定し、PR #23〜#32のhead、base、state、Draft、変更ファイル、CI、担当完了根拠を再確認する。
2. 各ownerの受入条件と依存順を確認する。局所完了していない実装は、そのownerが完了するまで取り込まず、担当・必要契約・検証条件を引継ぎ表に記録する。
3. 完了根拠のある子PRだけをintegration branchへ取り込み、shared-file conflictは書込みownerの契約に従って解消する。取り込み直後に個別のformatter、validator、runtime、regression、evalを実行する。
4. 実owner成果物を利用できる範囲で、ID／revision／scope／currentness／承認／CAS／履歴readbackと下流changed-scopeを接続し、独立fixtureの結果と区別する。
5. 全Skill同時routing／trigger、実Agent・実runner・実provider、S1〜S17、人間編集8ケース、QA全工程・開発連動QAの全完了条件を独立検証する。各workflowと各commandの結果を個別に判定する。
6. 担当文書、統合管理文書、PR #22本文を現在の結果へ同期する。未実施・SKIP・blocked・失敗は明示し、親PRの全完了宣言は全条件が揃った場合だけ行う。

## 検証

- 取り込みごとに、担当PRの指定unit／integration／regression、formatter・lint、deterministic／semantic／trigger dataset、公式Skill形式、Code Quality／Validate Agent Skills／Deterministic Output Evals／Semantic Output Evals／Codex Harnessを個別に確認する。
- 統合後はrepositoryの指定Python versionで全runtime・deterministic suiteを個別実行し、CI結果を同じheadの証拠へ結び付ける。
- 実providerはnative CAS、revision history、独立readback、認証された承認、権限不足・競合・失敗再開を検証する。実案件runnerとqa-training-storeはPlanの固定commitに対して対象を記録し、独立基準の期待結果と照合する。
- 15＋10条件、詳細01〜08、S1〜S17、人間編集8ケース、5効率シナリオの各結果をscope・evidence ref・owner・残件付きで記録する。

## 完了条件

- 担当PRの完了・未完了・blockedを全件照合し、統合対象の全owner成果物が正本契約と局所受入を満たす。
- 共有routing・README・EVALS・runtime・既存consumerの互換・migration・履歴と、ID／revision／承認／CAS／readbackを統合状態で検証する。
- 15＋10条件、詳細01〜08、S1〜S17、人間編集8ケース、5効率シナリオ、全required CIが根拠付きで完了する。
- 未接続の実環境条件がある場合は親PRを完了扱いにせず、blocked理由と再開条件を残す。

## 検証済み事実と仮定

PR状態・head・CI結果は2026-11-12のGitHub上の値を検証済み事実とする。新たな案件固有provider、実承認主体、製品CI、実案件sourceは確認できていないため、提供済みとは仮定しない。
