# PR #22 マージ判断の記録（2026-11-14）

本書は、PR #22（`feat/development-qa-traceability` → `main`）をマージする前の安全確認と、最終受入条件の未達を許容する判断の記録である。最終受入の個別判定・測定値・証拠の正本は[最終受入の検証記録](./evidence/final-acceptance-2026-11-12/README.md)とし、本書はその詳細を複製しない。

## 1. 判断の概要

- 判断の性質: 従来の最終受入条件が未達のまま、実案件で運用しながら改善する方針でマージを進めるための、**リスクを認識したうえでの許容判断**である。「全条件PASS」ではない。2026-11-14の再検査で新規露出が見つかったが、利用者は会話ログを残す判断をし、ホスト名風のテストセット識別子は保持する判断をした。ホスト名12値は会話ログ内のコマンド出力に含まれ、ログを残す判断に伴って残る。ホスト名の個別の所属（組織の機器か個人端末か）は確認できていない。マージは利用者の明示指示まで実行しない（§9.1）。
- 最終受入の状態: 未完了のまま。主要な未達3項目と、その他の未完了条件が残る（§5）。
- 確認結果: 有効な可能性がある認証情報は検出されなかった。前回検査（HEAD `59d56017`まで）では新たな個人情報の露出も見つからなかったが、その後の2026-11-14のマージ直前の再検査（§9.1）で新規露出と判定不能が見つかったため、この結論は維持できない。既存テストの回帰は無く、重大な認証・認可の回避やデータ破損の経路も確認されなかった。
- 修正: マージ前に、案件分離・入力検査・default branchへのpush拒否などに関する問題を修正し、回帰テストを追加した（§3）。
- 残存: 修正せず既知の制約として残す問題がある（§4）。運用で補う必要がある（§6）。
- 履歴書換え: 行わない。ユーザー名とsession UUIDを含む絶対パスなどの露出が残るが、除去には利用者の明示承認が要る（§9）。
- マージ実行: AGENTS.mdに従い、マージ操作は利用者の明示指示がある場合にだけ行う。本書はその指示の代わりではない。

## 2. 確認した重大リスクと結果

調査は2026-11-14に実施した。Claude Haiku 5.5のサブエージェント（A 機密情報検査、B 実装・セキュリティ確認、C CI・回帰・マージ影響、D 未達条件の受入整理、A2・A3 機密情報の追加確認、F1〜F3 修正、V 回帰検証）が担当し、親Agentが判断・統括・GitHub操作を担当した。調査対象のHEADは`59d5601744b32b1f7bec2e05e1cac75bdf04b62b`（CI全PASS）である。修正は後続のcommitで行い、そのHEADとCI結果はPR本文に記録する。本書は自身のcommit SHAを含めない。

### 2.1 機密情報

- 検査範囲（前回検査、HEAD `59d56017`時点。最新の正本は§9.1）: PR履歴の一意なblob 1,404件（現HEADに存在するもの1,179件、履歴のみ225件）、141 commitのmessageと作者・コミッター、`.jsonl.gz` 61件・`.tar.gz` 19件（中身4,276ファイル）、`.pyc` 13件。展開上限（200MiB）に達したものは0件。
- 未検査: PR以外のref・tag・git notes。main側の履歴は、メールアドレスの出現のみA2で確認した。
- 限界: 正規表現と高エントロピー検査によるため、未知の形式は見逃し得る。認証情報の有効性確認のための外部認証は行っていない。
- 結果（有効な可能性がある認証情報）: 0件。GitHub・Anthropic・AWS等のtoken、OAuth・refresh token、秘密鍵、Cookie、Bearer、URL内資格情報の実値は検出されなかった。検出されたAuthorization・Bearer・passwordなどの記述は、テストの偽値、環境変数参照、例示である。
- 結果（製品seedのPBKDF2形式ハッシュ）: Agent実行ログ2ファイルに9種類あった。うち7件は公開repo（qa-training-store、所有者は同一アカウント）の`src/seeds/password-hashes.ts`と一致する。これは教材用の固定パスワードであり、同repoの`docs/07_testability/seed_catalog.md`に明記されている。残り2件は同repoの公開docs由来である。新たな露出ではない。
- 結果（メールアドレス）: 次の3区分に分けて確認した。
  - 第三者の個人メールは、Co-authored-byとしてPR範囲の2 commitに含まれる。同じアドレスは既にmainの履歴に23 commitで存在する。
  - 社内ドメインの個人メールは、author・committerとしてPR範囲の22 commitに含まれる。既にmainの履歴に21 commitで存在する。
  - PR範囲にだけ現れる1種類（27 commit）は、AIコーディングツールが自動付与する公開のnoreplyアドレスである（Co-Authored-By: Claude Sonnet 5.5が65件、Claude Opus 5.5が5件）。個人のメールではない。
  - 結論（前回検査時点）: 新たな個人情報の露出は無い。この結論は、その後の再検査（§9.1）で新規露出と判定不能が見つかったため維持できない。
- 残る露出（低〜中）: §9に記載する。

### 2.2 実装・セキュリティ

- 認証・認可の回避、秘密情報の漏えい、データ破損の経路は、コード上では確認されなかった。
- 確認できた良い点:
  - 不正なpath（`..`、絶対path、`.git/`、`\`、予約名など）は拒否される。
  - CASの競合（古いexpected revision、create-if-absentの再実行）は拒否される。
  - 承認は書込みの前に判定される。
  - subprocessは`shell=True`を使わず、引数配列で呼び出す。
  - `update-ref <ref> <new> <old>`により、非fast-forwardは拒否される。
  - readbackは独立に検証される。
  - owner verifierが未登録のscope（F 3 Skill等）は`unverified_scopes`により完了不可となる。
  - `ci_handoff.py`はfail-closedである（hash不一致、source不一致、未分類、未承認などを拒否し、symlinkも拒否する）。
  - `.github/workflows/`はPR #22で変更されていない。sample workflowは`pull_request`・`contents: read`・commit pinである。

### 2.3 CI・回帰・マージ方法

- CI（HEAD `59d56017`）: CodeQL、Analyze×3、code-quality、codex-contract、deterministic-output-evals、semantic-output-evals、validate、windows-launcherがpass。CodeRabbitはリポジトリstar数の条件によりskipped（非required）。`render`・`vercel`のcheck suiteはqueuedのまま（外部integration、非required。意味は未確認）。
- 回帰: runtimeテスト1,039件中1件が失敗した。これはPython 3.12起因の既知の`test_ci_handoff`のJSON nestingである。deterministic 670件はOK、semantic 14件はOK、`semantic/validate.py`はOK。
- PR状態: OPEN、非Draft、mergeable CLEAN。141 commit（merge commit 2件を含む）、変更1,262ファイル（+189,580／-868）、削除0・rename 0。`.github/`と`.codex/`に差分は無い。
- ruleset `protect-main`: required status checksは`validate`・`deterministic-output-evals`・`semantic-output-evals`。non-fast-forward禁止・削除禁止・linear history。required approving reviewは0件。
- リポジトリ設定: merge commit不可、rebase不可、squashのみ可、merge後にbranch自動削除。
- baseの`main`は未更新（78d8d394）。

## 3. マージ前に修正した問題

修正はすべて回帰テストを追加したうえで行った。

1. **問題A（中）: Git providerの案件分離**
   - 内容: `GitArtifactStore`は成果物の同一性をpathだけで決めていた。そのため、別案件の文書を`read_current`で読めた。また、別案件のauthorizer承認で上書きできた。`persist_prepared`経由は防がれていたが、`store.write`の直接呼出しは防がれていなかった。
   - 修正: 既存pathを最後に変更したcommitの件名（`qa artifact: <kind> <path>`）と`QA-Project-Ref`を、読出し・revision指定読出し・既存pathへの書込みで検査する。不一致またはtrailerなしのcommitは`artifact_project_mismatch`で拒否する。拒否は、commitとref更新の前に行う。create-if-absentは対象外。
   - テスト: 5件追加（別案件の読出し・書込みの拒否とrefが進まないこと、別kindの拒否、trailerなしcommitの拒否、同一案件は従来どおり成功）。既存テスト1件のsetupを、storeが書くcommitと同じ形に変更した（assertionは変えていない）。`data-contract.md`に記述を追記した。
2. **問題H（低）: commit messageの改行文字**
   - 内容: U+2028・U+2029・U+0085などの改行文字を値に入れると、別行の偽trailerを作れた。
   - 修正: `\x0b \x0c \x1c \x1d \x1e \x85 U+2028 U+2029`を拒否する。テストを追加した。
3. **問題E（中）: `input_revision.py record`の任意file置換**
   - 内容: `--state`に任意のpathを指定でき、任意のfileをJSONで置換できた。
   - 修正: stateのbasenameを`input-revisions.json`に固定する（`state_name_not_allowed`）。既存fileが空でなく、`schema_version: input-revision-v1`のJSON objectでなければ上書きしない（`state_not_a_record`）。NUL文字を含むpath・root・stateは`invalid_path`（exit 2、JSON出力）で拒否する。
   - テスト: 5件追加（計19件）。
4. **問題C（文書）: `owner_verifiers.py`のdocstring**
   - 内容: 「自己申告のverifiedを受け付けない」と書かれていたが、evidence（保存本文・readback）は呼出し元が渡す。
   - 修正: docstringを実態に合わせた。実態は、渡された本文のhash一致、ownerの本番CLIによる検証、登録ごとのcurrentnessの確認までであり、保存先providerを独立に読み直してはいない。コード変更は無い。
5. **問題K（低〜中）: default／protected branchへのpush**
   - 内容: `testware-implementation/scripts/publish_git.py`は、plan JSONのbranchへ`--force-with-lease`でpushする際に、default／protected branchを検査していなかった。AGENTS.mdの方針と食い違っていた。
   - 修正: `main`・`master`（`refs/heads/`接頭辞・大文字小文字・末尾`/`の揺らぎを含む）と、取得できる場合はremoteのdefault branch（`symbolic-ref`）を、pushの前に`protected_or_default_branch_refused`で拒否する。
   - テスト: 2件追加（ローカルのbare repoのみ使用）。`SKILL.md`に1句追記した。

## 4. 修正せず既知の制約として残す問題

| 区分                                 | 問題                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 運用上の扱い                                                                                                                                                                                                                                                |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 保存済みselectionのcurrentness（中） | `e2e-test-selection`のowner verifierは、保存時点のcurrentnessのみを見る。その後sourceが変わっても現在のsource revisionと照合しない（`test-item/condition`・`test-reporting`は照合する）。そのため、保存済みselectionはsource変更後も完了扱いになりうる。                                                                                                                                                                                              | selectionの完了は保存時点のcurrentnessのみとみなす。source変更後は再検証する。                                                                                                                                                                              |
| 必須Skillの省略（完了判定）          | `workflow_runtime`は、`workflow_scopes`に含まれないSkillを検査しない。必須Skillの省略を検出する仕組みは無い。F 3 Skill（test-requirements-analysis・test-architecture-design・test-management）はowner verifier未登録で、scopeに含めれば完了不可になるが、省略すれば検出されない。stateの「完了」欄は手動で記入できる。                                                                                                                               | F行を完了と記録せず、F成果物を検証済みとして引き継がない。                                                                                                                                                                                                  |
| workflow_refの未結合（中〜低）       | `workflow_runtime`は`workflow_ref`を判定入力と結び付けない。別の`workflow_ref`で同じscopesを渡しても結果は同じになる。                                                                                                                                                                                                                                                                                                                                | 呼出し側の規律に任せる。                                                                                                                                                                                                                                    |
| 入力revisionの列挙漏れ               | `input_revision.py`は、呼出し側が渡したpathだけをhashする。列挙から漏れた入力が変わっても`same`になりうる。                                                                                                                                                                                                                                                                                                                                           | 入力の列挙の完全性を呼出し側が担保する。                                                                                                                                                                                                                    |
| owner verifierのreadback             | readbackは呼出し側（Agent）が渡す申告であり、provider読戻しの証明ではない（docstringに明記済み）。                                                                                                                                                                                                                                                                                                                                                    | 保存先providerの確認は別途行う。                                                                                                                                                                                                                            |
| 評価harnessの権限（中〜高）          | `efficiency/harness.py`と`trigger/run.py`は`--permission-mode dontAsk`で、`Write`・`Edit`をpath無制限で許可し、`Bash(python3:*)`を許可する。違反は事後検出のみ。評価harnessは検証ツールであり、Skill本体には含まれない。隔離環境（書込みはworkspaceのみ、credentialsをmountしない、network無効）での実行を前提とする。Skillの文章だけでは制限にならない。効率比較では、qa-state外への補助script書込みが3/10試行で発生した（製品ツリーの変更は無し）。 | 隔離環境で実行する。Claude Codeの`permissions`の`Write(<path>/**)`形式の制限は動作を確認したが、Agentが作業を止める副作用があった。このrepoに`.claude/`設定は無く、sandbox・hookは未構成である（Codex向けの`.codex/`はClaude Code sessionには掛からない）。 |
| 共有予約                             | 共有予約providerが無い。同一案件の並列workflowは呼出し側の規律に依存する。`isolated=True`の申告は検証されない。`qa-state/`のMarkdown stateは直接書込みでロックが無い。Gitに保存した成果物はnon-fast-forwardで同時書込みが拒否される。並列実行の実挙動は未検証。                                                                                                                                                                                       | 同一案件の並列実行は避ける（§6）。                                                                                                                                                                                                                          |
| sample（`product-ci/`）              | 分類（classification）の中身は検証されない。`build_expected.py`は`qa/`配下の`.md`のみ列挙する（Git storeは`.json`も許可）。verification用のsampleであり、mainに統合する製品CIではない。                                                                                                                                                                                                                                                               | 製品CIとして扱わない。                                                                                                                                                                                                                                      |
| Native Jestのcold実行                | 既存証拠では、assertion不一致ではなく、Jestの既定test timeout（5秒）の超過である。同じテストはwarm実行で合格する。対象は製品repo（qa-training-store）のテストで、本PRの差分には含まれず、このrepoのCIはこれを実行しない。原因（jest-expoの初回変換コスト）は推定であり、直接の証拠は無い（未確認）。timeout値の変更・テストの無効化は行っていない。                                                                                                   | 未確認の原因として残す。                                                                                                                                                                                                                                    |

## 5. 許容する未達

個別の判定・測定値・証拠は[最終受入の検証記録](./evidence/final-acceptance-2026-11-12/README.md)の§8・§9を正本とし、本節は要点のみ示す。

### 5.1 主要な未達（3項目）

1. **trigger評価**: 肯定8 queryと否定1 queryが不合格（validationでは肯定20/28・否定27/28 queryがpass）。description調整は1回目のみ採用し、2回目・3回目は不採用として打ち切った（最終受入記録§7.2）。
2. **効率比較は未実証**: 比較器の総合判定は`unproven`。所要時間は5シナリオのうち4シナリオで改善した。変更なし再依頼では悪化した。費用・tokenは悪化するシナリオが残る。安全または品質が未達の試行が5件残る（実行5の6件から3件に減ったが解消していない）。改善はここで打ち切り、効率向上は未実証のまま最終とする（最終受入記録§8・§9）。
3. **F 3 Skillの完了検証入口の欠落**: test-requirements-analysis・test-architecture-design・test-managementは、保存・readback・currentnessを検証する本番入口が無い。owner verifierを登録すると形式検査を「完了」と偽るため、登録していない。完了は引き続き不可である。

### 5.2 その他の未達

最終受入記録§9の「その他の未完了条件」に従う。主なものは次のとおり。

- 実製品の全機能抽出。
- 実PRのmerge・rebase・実build。
- 実案件データでの分類・算出・source inventory・通し。
- 統合受入。
- 実Playwrightでの確認。
- 実外部資料の改版入力。
- 修正確認の実接続、Activityの保存readback、修正通知と周辺Regression。
- 改善採用の承認と正本改版。
- 共有予約provider、承認失効・実行中断・取得失敗、中断後の別セッション復旧。
- 承認済み配置の実運用。
- 実runnerの個別事項（Native Jestのcold実行FAIL）。

利用者が2026-11-13に承認した対象外（API-only・batch・非機能・直接TCのrunner、releaseを含む通し、実Q06の配置合意、外部Issue管理先の設定、Codexでの受入、Windows実行、効率比較の人間のレビュー・承認時間）は維持する。既存の判定表の値はPASSへ変更しない。

注記: 最終受入記録の該当欄に記載が無い項目（詳細03、S8、S10、S14、S15、詳細08、開発連動#13の注記など）は、記録側でも「既存表に記載なし（未確認）」と注記されている。本書では判定を補わない。

## 6. マージ後の運用上の制約

判定は「実行可能性」の欄に示す。

| 制約                                                | 実行可能性 | 補足                                                                                                                                                                                    |
| --------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agentの書込み範囲を実行環境側で制限する             | 一部可能   | `--allowedTools`のパス指定ルールは動作確認済み。`Bash(python3:*)`が残ると任意の場所へ書けるため、書込み制限だけでは境界にならない。OS・コンテナによる隔離が必要で、このrepoでは未構成。 |
| 重要な製品コードの変更に人間のレビューを残す        | 運用のみ   | CODEOWNERSは無い。rulesetのrequired approving reviewは0件。                                                                                                                             |
| 同一案件の並列workflowは共有予約の確認まで避ける    | 運用のみ   | 強制する仕組みは無い。                                                                                                                                                                  |
| F 3 Skillの成果物を検証済み完了として扱わない       | 一部可能   | scopeに含めれば完了不可になる。省略は検出されない。                                                                                                                                     |
| 保存・承認・readback・currentnessの検証を省略しない | 一部可能   | Git providerは独立したreadbackと承認主体の確認を行う。owner verifierのreadbackは呼出し側の申告である。                                                                                  |
| 初めて利用する実案件では成果物と実行結果を確認する  | 実行可能   | 人間の手順。自動強制はできない。                                                                                                                                                        |
| 未達・不具合はIssueに再現条件と影響を記録する       | 一部可能   | Issueテンプレートは無い。Issueの作成自体は可能。                                                                                                                                        |

## 7. 実案件で継続検証する事項

実案件での運用中に、次を確認する。結果は最終受入記録の残件、または該当Issueへ記録する。

- Riskを踏まえたfail／warning／blockedの分類、実案件データでの算出、source inventory。
- 承認済み配置の実運用（実Q06の配置合意は対象外のまま）。
- F 3 Skillの成果物は、検証入口が整うまで完了として扱わない。
- 共有予約の必要性と、同一案件の並列実行の挙動。
- trigger評価の誤判定（肯定・否定の不合格query）が実案件で起きるかどうか。
- 効率の悪化したシナリオ（変更なし再依頼など）と、安全・品質が未達の試行の発生頻度。
- 保存済みselectionのsource変更後の再検証（§4）。
- 入力revisionの列挙の完全性（§4）。
- 意味評価の停止条件は現状維持であり、入力不足で停止する挙動を変えていない（利用者承認 2026-11-13）。

## 8. マージ方法と注意点

- マージ方法はsquashのみ可能。142 commit（現HEAD `4dc2a082`時点。前回記録の141 commitは HEAD `59d56017`時点の値）が1 commitになる。
- merge後、branch `feat/development-qa-traceability`はリポジトリ設定により自動削除される。親Agentは削除操作をしない。
- 影響（推定を含む）:
  - PR本文のbranch絶対リンク（`blob/feat/development-qa-traceability/...`）4件は、削除後に404になる見込み。マージ後にmainの同じ文書へ更新する。
  - 文書内にbranch名の文字列が13ファイル43行ある（リンクではない）。
  - 証拠・文書は主にcommit SHAで参照している。PR branchのcommit（HEADの祖先19件）は、squash後にmainの履歴には存在しなくなる。
  - `actions/runs/`リンク126件は、runが残る限り有効。
- 作業終了時のプロセス確認（2026-11-14）: WSL・Windows側のプロセスを確認した。今回の作業に由来する不要なプロセスは見つからず、終了したものは0件。ただし本作業の起動ではない古いbashシェル1件（PID 264861、約16時間前から残存し、子のcatが入力待ち）が残っており、終了していない。
- squashの既定のcommit messageは、複数commitのPRでは各commitのmessageと`Co-authored-by`を本文に並べうる。第三者のメールアドレスを含むCo-authored-byが2 commitにあるため、squash時のcommit messageは手で整える。具体的には、`Co-authored-by`を含めず、本文を明示的に指定する。これはマージ実行時の操作であり、履歴の書換えではない。

## 9. 履歴書換えを行わない判断と残る露出（利用者の判断事項）

- 判断: 履歴書換えとforce pushは、利用者から今回与えられていない権限であり、行わない。有効な認証情報は形式検査の範囲で検出されなかった。新たな個人情報の露出の扱いは§9.1を参照。
- 残る露出（低〜中）: 以下は前回検査時点の一覧である。2026-11-14の再検査で判明した新規露出（会話ログ61ファイルのsessionId、ネットワーク共有パスのホスト名12値、端末ユーザー名の別形など）は§9.1を正本とする。利用者は会話ログを残す判断をした（§9.1）。ホスト名12値は会話ログ内のコマンド出力に含まれ、ログを残す判断に伴って残る。ホスト名の個別の所属（組織の機器か個人端末か）は確認できていない。
  - ローカルのWindowsユーザー名とsession UUIDを含む絶対パスが、evidence（docs・gz・tar.gz）に残る。ユーザー名は公開GitHubアカウント名と同系統である。2026-11-14にアーカイブ以外の28ファイルは置換済み（§9.1）。アーカイブ内は未置換。
  - `credential_expires_at`が51ファイルのログに残る。ISO時刻のみで、トークンは含まない。
  - `session_id`・`uuid`が多数残る。認証情報ではない。
  - 製品repoの逐語的な内容がログに残る（Read約90万字ほか）。製品repoは公開で、ライセンスは未設定、所有者は同一アカウント。
- ログ生成処理: `scripts/skills/evals/trigger/run.py`と`efficiency/harness.py`の`clean_environment()`は除外リスト方式である。親sessionの環境変数のうち指定10キーだけを除き、他は子プロセスへ継承しうる。ログへの環境変数値の出力は検出されなかった。認証ファイルは`make_config_dir()`がsymlinkで参照するだけで、コピーはしない。リポジトリにsymlinkは0件。
- 除去の方法と条件: 上記の露出を除去するには履歴書換え（force push）が必要であり、利用者の明示承認なしには実施しない。
- 注意: PRのbranchは既にpush済みで、GitHub上で公開されている。branch削除後も、PRの参照から履歴は到達しうる（推定）。
- 利用者の判断事項: (a) 上記の露出を受け入れたままマージする、または (b) 除去のための履歴書換えを明示的に承認する。前回検査時点では(a)を前提とした許容判断だった。2026-11-14に利用者は会話ログを残す判断をした（§9.1）。ホスト名12値はその判断に伴って残り、個別の所属（組織の機器か個人端末か）は確認できていない。マージは利用者の明示指示まで実行しない。(b)の承認は含まない。

### 9.1 マージ直前の個人情報・機密情報の再検査（2026-11-14）

- 目的: 公開される証拠に個人情報・機密情報が残っていないかを、マージ直前に再確認する。
- 実施: Python検査scriptで行った。scriptはリポジトリ外で作成・実行し、commitしていない。合成データによる検査script自身の自己検査は61件すべてPASSした。
- 範囲:
  - main..HEADの142 commit（author・committer・message・branch名）。
  - PR側の一意なblob 2,443件（履歴の新規分とHEADのツリー）。うち`.jsonl.gz` 61件、`.tar.gz` 19件（中身の検査済みファイル4,276件を含む）。
  - 検査失敗0件、対象外0件。
- 結果（種類別の結論のみ。実値は記載しない）:
  - 実トークン形式（主要サービスのtoken接頭辞、JWT、PEMの秘密鍵）は、base64のデコード結果を含めて0件。
  - 環境変数の代入に見える32値は、main未掲載のもので、コードの代入式・識別子・パスである。
  - 認証ヘッダー・Bearerの検出は、散文・型注釈・テストの期待値である。
  - テストfixtureの2値は、秘密検知のテスト入力（期待値）である。
  - PBKDF2の新規8値は、公開製品repoのseedと公開docsの固定値と一致する。公開された教材値の再掲載であり、新たな露出ではない。
  - 電話番号形式に見えた新規2値は、16進IDの断片による誤検知である。
  - 個人向けメールアドレスの2値は、既存のmainにも存在する。
- 既存結論との関係:
  - 「有効な認証情報0件」は、形式検査の範囲で維持する。
  - 「新たな個人情報の露出なし」は維持できない。新規の露出は次のとおり。
    - (a) 効率比較の評価ハーネス（headless）の会話ログ61ファイル。sessionIdを含む。認証値・URL・Cookieを伴わない実行識別子である。環境変数のダンプ、認証情報ファイルの内容、利用者のhome外の内容、外部サービスの呼出しは検出されなかった。
    - (b) 端末ユーザー名の別形1 blob。同一人物の既存識別子がmainにもあり、追加の識別は小さい。
    - (c) PBKDF2の再掲載（公開教材値）。
    - (d) ネットワーク共有パスのホスト名12値。会話ログ内のコマンド出力に由来する。固有名だが、組織の機器か個人端末かは確定できていない。
- 組合せ: 端末ユーザー名がGitHubの公開アカウント名の接頭辞と一致するものが27 blobあり、組み合わせると個人を特定しやすい。
- 判定不能として残るもの: (d)のホスト名12値の所属、会話ログ61ファイルの公開継続可否、thinkingの署名データ（不透明で内容を確認できない）。2026-11-14に利用者は会話ログを残す判断をした（下記）。ホスト名12値は会話ログ内のコマンド出力に含まれ、その所属（組織の機器か個人端末か）は確認できていない。thinkingの署名データは利用者の判断に含まれず、未確認のまま残る。マージは利用者の明示指示まで実行しない。
- 件数の差:
  - 既存記録の「141 commit」はHEAD `59d56017`時点の値である。現HEAD `4dc2a082`では142 commitである。
  - 前回検査（§2.1、1,404 blob・141 commit）と今回の再検査（2,443 blob・142 commit）は検査基準が異なる。今回の再検査（§9.1）を最新の正本とする。
  - 既存記録の「1,179 blob」はどの集計基準でも再現できず、基準は不明である。今回の一意blobはHEADのツリーで2,208件である。
- 取扱い:
  - 履歴書換え・force pushは行わない（§9の方針）。
  - squash mergeとbranch自動削除では、PRの履歴や公開済みの内容がGitHub上から消えるとは判断しない。
  - 除去が必要と利用者が判断した場合の選択肢は、(1) 公開範囲の変更、(2) 履歴書換え（利用者の明示承認が必要）、(3) HEADからの削除のみ（履歴には残る）である。
- 利用者の判断（2026-11-14）: リポジトリは非公開にしない。会話ログ（アーカイブ）は残す。ログ以外の個人情報はサニタイズする。公開GitHubオーナー名とテストセット識別子（ホスト名風の文字列）は保持する。履歴書換え・force pushは行わない。マージは利用者の明示指示まで行わない。
- 実施（コミット `50f1bdc4`、通常push）: 値を置換した28ファイル（docs 10、証拠JSON・データ 18）と、sha256記録を更新したtrial.json 4件、計32ファイルについて、端末ユーザー名（パス内）、依頼者の氏名（文中）、実行UUIDとsessionIdを、プレースホルダ（`<USER>`、`<HOST>`、`<USER-SHORT>`、`<REQUESTER>`）と固定のダミーUUIDへ置換した。連動して、`run3-candidate-final`のtrial.json 4件に記録されたworkflow-state.jsonのsha256を更新した（更新後の値は現ファイルと一致を確認）。hashやサイズを参照する他の箇所は無い。
- 検証: 作業ツリーの再検査で置換対象の残数は0。変更は32ファイル（+52／-52）のみ。dprint checkはOK。deterministic 670件・semantic・runtimeはOK（既知のPython 3.12依存の1件を除く）。
- サニタイズしていない範囲: 会話ログ・圧縮アーカイブ内（端末ユーザー名のパス、sessionId、ネットワーク共有パスのホスト名を含む）、過去コミットの置換前の内容、commitのauthor／committerメタデータ、公開GitHubオーナー名、テストセット識別子（ホスト名風）、ホスト付きサンドボックス用アカウント名（個人名ではない）9件・3ファイル。日本語の人名と文書中の「依頼者」「承認者」の記述は自動検出できず、未確認。
- 認証情報系の検出（ENV-SECRET等）は個人情報の置換の対象外であり、report_triageの既存分類に従う。
- **個人情報の確認結果**（2026-11-14、追加確認）:
  - 対象: git管理の2,298ファイルのうち、テキスト系2,217ファイル。アーカイブ80件とバイナリ1件は対象外。会話ログ・圧縮アーカイブは検査していない（未検査）。
  - 方法: 敬称、役割ラベル（依頼者・承認者・担当・実行者・署名・作成者・レビュー・owner・author・approver・reviewer・requested by等。表セルは228行を全件目視）、JSONのperson系キー、一般的な姓の辞書（約150語）、ローマ字・カタカナ中黒の形状、端末ユーザー名のASCII形、ユーザーディレクトリ、メール、UUID、電話番号形式、内部ドメイン、UNC、サンドボックス系の記述、会社名・郵便番号などを、文脈を読んで候補ごとに分類した。
  - 結果: 実在人物の氏名と判断できるものは検出されなかった。今回新たにサニタイズが必要な個人情報も見つからず、変更は無い。判定不能は0件（自動検査と文脈確認の範囲での値であり、辞書にない姓や、役割語も敬称もない文中の氏名は検出できない可能性が残る）。
  - 既に承認・保持した公開情報（置換の対象外）: 公開GitHubオーナー名（端末ユーザー名のASCII形236件は、いずれも公開オーナー名の一部。この件数は独立には再検証していない）、テスト用の固定UUIDと50f1bdc4の固定ダミーUUID、`example.invalid`のメール26件、例示のユーザーディレクトリ表記、sandbox系の汎用的なアカウント名（個人名ではない）。承認済みテストセット識別子（ホスト名風）は、特定・検証せず保持のみ。
  - 検査できなかった範囲: 会話ログ・圧縮アーカイブ、過去コミットの置換前の内容、commitのauthor／committerメタデータ（置換の対象外）。
  - 自動検査の限界: 人名は、敬称・役割語・辞書にある一般的な姓・ローマ字・カタカナ中黒の形状で検出した。辞書にない姓や、役割語も敬称もない文中の氏名は検出できない可能性がある。英語の辞書は使えず、ローマ字の絞り込みは発見的な方法である。日本語の人名と文書中の「依頼者」「承認者」の記述は自動検出できず、未確認。
- **証拠の整合性**（2026-11-14、追加確認）:
  - 対象: commit `50f1bdc4`の32ファイル（md 10、json 21、txt 1）。
  - hash: `run3-candidate-final`の4 trialの`workflow-state.json`のSHA-256を、作業ツリーのbytesとHEADのblobのbytesの両方で再計算し、trial.jsonの記録値と4/4一致した。置換前の記録値は、commit `50f1bdc4`の親のblobのbytesのsha256と4/4一致した。サイズは置換前後で同一。
  - 旧sha256（全長と先頭7・8・12・16桁）と旧blob oidは、HEADの追跡docs全体と全アーカイブ内部で検索し0件（陽性対照で検出を確認）。
  - 識別子: 置換前のUUID10種類と置換後のダミー10種類は1:1に対応する。同じ元値は同じダミーになり、出現件数は置換前後で一致。4つの`workflow-state.json`の`workflow_ref`は同一。
  - 測定値・判定: `run3-candidate-final`のtrial.jsonと`workflow-state.json`の構造比較で、差分は`workflow_ref`と`artifacts.workflow-state.json`の2項目のみ。judge・quality・deterministic・metrics・数値は一致。他のjson（static、trigger）とtxtは置換規則で完全に再現できた。
  - 記録の追加: 4件のtrial.jsonにトップレベルキー`sanitization`（commit、注記、`workflow_state_sha256_before_sanitization`）を追加した。既存キーの値は変更していない。hashやサイズを参照する箇所は無く、読み込む既存コードは未知のキーを無視する。
  - 元ログとの関係: 会話ログは未サニタイズのまま保持する。置換後のJSONと元ログを結ぶ対応表はリポジトリに無い。対応づけは、trial名・試行番号、または親commitとの比較に限られる。置換後の`workflow-state.json`は実行時点のbytesと同一ではない（hashは置換後ファイルのもの）。runtimeの`workflow_ref`の機械照合は、置換後のJSON単独ではできない。
  - 修正前から存在し、今回は未修正の事項: trial.jsonの`artifacts`のsha256は、456件中、現在の同名ファイルと一致が6件、不一致が350件、対応ファイル無しが100件（原因未確認）。件数は、同名ファイルを探す規則（探索範囲、supersededの扱い）によって変わる。別の探索規則（trial配下で同名ファイルを探索し、supersededを除外）では、一致6・不一致341・対応なし109だった。どちらの規則でも一致は6件で、artifactsのhashを現ファイルの同一性の証拠として扱えない点は変わらない。このため`artifacts`のhashを現ファイルの同一性の証拠として扱えない。trial.jsonの`sessions.log`は`session1.jsonl`と記されるが、実ファイルは`session1.jsonl.gz`である。`comparator-input.json`の`artifact_ref`・`independent_evidence_ref`のパスは実際の配置と一致しない。
  - 未確認: 実行時点のbytesと50f1bdc4の前のbytesの同一性は、記録hashとの一致からの間接確認のみ。artifacts hash不一致の原因。サイズ表記の全文検索の一部。
  - 今回新たに判明した個人情報の問題: なし。証拠整合性の制約は上記のとおり（既存問題を含む）。既存の最終受入条件の判定は変更していない。
- 未実施: 外部認証による有効性確認は行っていない。正規表現と高エントロピーの検査のため、未知の形式は見逃し得る。

## 10. 判断の根拠と対象

- 対象: PR #22（`feat/development-qa-traceability` → `main`）。調査対象HEAD `59d5601744b32b1f7bec2e05e1cac75bdf04b62b`。調査日2026-11-14。
- 根拠:
  - §2の調査結果（機密情報、実装・セキュリティ、CI・回帰・マージ方法）。
  - §3の修正と回帰テスト。
  - [最終受入の検証記録](./evidence/final-acceptance-2026-11-12/README.md)の§8・§9（個別判定の正本）。
  - 利用者の2026-11-13の対象外承認。
- 限界:
  - 機密情報の検査は、PR履歴の範囲に限る。未知の形式は見逃し得る。認証情報の有効性は確認していない。
  - 実案件での運用実績は無い。
  - Codexでの受入は未検証であり、対象外として扱う。
  - Windows実行は設計上非対応であり、対象外として扱う。
- マージ後にmainの同じ文書へ更新する対象: 本書を参照するPR本文の文言。

本書はPR #22の最終受入完了ではなく、リスクを認識したマージ判断の記録である。最終受入は未完了のまま。
