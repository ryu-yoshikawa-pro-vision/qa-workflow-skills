# PR #22 現在の統合・最終受入計画

## 目的

PR #22を、既存の開発連動QA Plan、QA全工程Plan、詳細01〜08、統合管理READMEの受入契約に従って統合する。既存の15＋10完了条件、S1〜S17、人間編集8ケース、5つの効率比較シナリオを変更・省略しない。この計画は実行順と現状を記録し、既存Planの代替にしない。

## 現在の状態と根拠

2026-11-09時点でPR #22はopen、base `main`、integration branch `feat/development-qa-traceability`、head `7cc8ac8bcebdacd6ac35aede3bed8555c73f276c`。このheadのCode Quality、Validate Agent Skills、Deterministic Output Evals、Semantic Output Evals、Codex Harnessはすべてsuccess。

| 担当PR | 現状 | CI・依存 |
| --- | --- | --- |
| #23 A | merged。共通runtime・保存／承認／CI基盤を統合済み | head `2c2dcab` の5 workflow success。実provider・認証主体・製品CI・実Agent統合は未接続 |
| #24 B | open、ready for review。Project Context・feature-analysis実装あり | head `7bc6395` の5 workflow success。実案件・実providerの横断接続は未検証 |
| #25 C | open、Draft。UI分析・人間編集実装と局所受入を完了 | head `fba2b38` でCode Quality／Deterministic／Semantic／Codex Harness success。Validate Agent Skillsは共有README catalog不足でfailure |
| #26 D | open、Draft。item／condition候補の実装と局所評価あり | head `9afd18f` の4 workflow success。実provider、B/E成果物との接続、実Agent評価は未完了 |
| #27 E | open、Draft。作業文書のみで実装コードなし | 担当Eの実装・局所受入待ち |
| #28 F | open、Draft。作業文書のみで実装コードなし | 担当Fの実装・局所受入待ち |
| #29 G | open、Draft。非E2E testware／execution実装あり | head `2650c7d` の4 workflow success。実案件runner・provider・H/J接続は未完了 |
| #30 H | open、Draft。作業文書のみで実装コードなし | 担当Hの実装・局所受入待ち |
| #31 I | open、Draft。作業文書のみで実装コードなし | 担当Iの実装・局所受入待ち |
| #32 J | open、Draft。作業文書のみで実装コードなし | 担当Jの実装・局所受入待ち |

証拠は各担当PRのhead・Checks・作業定義を正本とする。Draftのコードやfixtureを、担当完了・実環境受入として扱わない。

## 既存契約

- 最終統合先はPR #22の`feat/development-qa-traceability`。担当の独立実装は各owner PR、親PRは取り込み・接続・横断検証・最終判定を行う。
- 共有runtime・README・EVALS・CIの実装ownerはA。UI package関連既存経路はC。担当所有外のruntimeや正本を親PRへ複製しない。
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

- #25のValidate Agent Skills failureはREADMEに`ui-target-analysis`が未登録であることに起因し、READMEのA ownershipと共通route／EVALSの同期が必要。
- #24/#25/#26/#29のopen／Draft状態と局所受入の差を確認せずに取り込むと、未完了契約や重複共有ファイルを親PRへ持ち込む。
- #27/#28/#30/#31/#32に実装がないため、現時点ではPR #22全体の完了条件を満たせない。
- provider、権限者、実案件データ、製品CI接続がない条件は、必要な権威ある入力が揃うまでblocked。

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

PR状態・head・CI結果は2026-11-09のGitHub上の値を検証済み事実とする。新たな案件固有provider、実承認主体、製品CI、実案件sourceは確認できていないため、提供済みとは仮定しない。