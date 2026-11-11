# PR #17：ChatGPTサブスクリプション認証と実Agent評価準備

作成日：2026-10-24\
対象branch：`feat/agent-eval-runner`\
確認開始時のHEAD：`a9d2ed36ac774a2da608ea25abb5703ad36f0fef`

## 1. 変更前の認証経路

旧`_auth_material()`は、`auth.json`が存在すれば方式を判定せず一時領域へ複製し、存在しない場合は`OPENAI_API_KEY`を認証に使っていました。ファイルの存在だけではChatGPTログインとAPI Keyを区別できず、API Key環境変数へのfallbackもユーザー制約に反していました。

## 2. 修正後の認証方式

schema 2の正式WSL2 launcherは、固定runtimeのCodex CLI 0.163.0に`codex login status`を実行させ、終了コードが成功し、出力がChatGPT loginと一意に判定できた場合だけ認証を受け入れます。API Key、未ログイン、不明な方式、実行失敗・timeout、無効な認証file、認証方式を確認できないstore、CLI version不一致は拒否します。ChatGPTを示す文言があっても終了コードが非0なら`check_failed`として拒否します。

状態確認subprocessには最小環境だけを渡し、`OPENAI_API_KEY`、`CODEX_API_KEY`その他の親環境を継承しません。stdout/stderrはメモリ上で分類し、生出力・認証file本文・認証file hashを表示または証拠保存しません。`--auth-status-only`は同じruntime照合と状態判定を行い、モデルを呼び出しません。

ChatGPTと判定した場合に限り、WSL2内の正規`auth.json`をAgent/Judge/Repairごとの一時`CODEX_HOME`へ複製します。API Key環境変数へのfallbackはありません。Windows filesystem、Windows側のCodex home、repository内のCodex homeは認証元として探索・利用しません。

## 3. WSL2で確認した状態と固定runtime

`/home/sella/.codex`を`CODEX_HOME`に指定し、ext4上のclean checkoutから`--auth-status-only`を実行しました。出力は秘密を含まない次の分類だけでした。

```json
{
  "authentication_check_status": "verified",
  "authentication_method": "chatgpt_login",
  "codex_cli_version": "0.163.0",
  "runtime_digest_status": "verified",
  "status": "verified"
}
```

固定runtime照合結果：

- Codex CLI：`codex-cli 0.163.0`
- package SHA-512：`bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3`
- Codex binary SHA-256：`399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215`
- 同梱bwrap SHA-256：`77360cb751ccedc5971391444ac86a8a33c15b04d6b4a6fe45f5d25496e62c4c`

`auth.json`の内容・hashは参照も出力もしていません。Windows認証の探索・複製、新規ログイン、モデルAPI呼び出しも行っていません。

## 4. 回帰テストと検証

認証の合成回帰テストは、ChatGPT login受入、API Key・未ログイン・不明方式・status失敗・timeoutの拒否、API Key環境変数だけの環境で実行不可、子環境からAPI Key変数を除外、方式不明のstore・不正なfile・Windows path・CLI version不一致の拒否、診断の秘密情報非表示を確認します。追加した非0終了コードの回帰テストは、ChatGPT成功文言だけで認証を通さないことを確認します。

WSL2で行った合成テストの結果：

- Agent評価suite：134 tests、2 skipped、成功
- Agent repository contract：4 tests、成功
- `improve.py`関連：41 tests、成功
- Semantic dataset validator：22 skills、163 casesを検出
- Semantic runtime/repository suite：27 + 13 tests、成功
- Deterministic runtime/repository suite：13 + 293 tests、成功
- Runtime contract suite：371 tests、成功
- WSL2 launcher integration：1 test、成功
- `compileall`（Agent評価runtime/tests）、成功

Windows上のlauncher transport testは8 tests成功しました。これはWindows PowerShell 5.1 / 7経路を対象とし、Codex認証・モデル呼び出しは行いません。

変更したREADME・Plan・reportはdprint 0.55.2でcheckし、`git diff --check`も成功しました。Ruffはこの作業環境にCLI/moduleがなく、ローカル実行できていません。依存追加は行わず、Ruffの最終確認はCode Quality CIで行います。

## 5. 隔離条件と残留リスク

WSL2二重bubblewrap、固定runtime、attemptごとのworkspace/output/temp `CODEX_HOME`、Agent/Judge/Repair間の認証領域分離、FD非継承、inner shellのnetwork制限、timeout後cleanup、final-message安全化は維持します。Host home、Windows filesystem、Evaluator-only資料はAgentからmountされません。Codex親processの外向きnetworkはモデル通信に必要なため維持します。

過去の合成認証marker実測では、Codex shellから一時認証fileを読めました。この残留リスクは今回も解消しておらず、observationsの`authentication_shell_visible_risk=true`を維持します。ChatGPT loginへ限定しても認証情報のshell可視性はなくなりません。実認証を使うAgent/Judge runは、このリスクを理解した明示承認が確認できるまで開始しません。

今回のWSL2 launcher integrationは合成データによるsandbox・FD・path・network・timeout cleanup確認です。選択モデルを含む最終profileへ紐付く新しいformal `isolation.json`はまだ生成していません。

## 6. 初回smokeの準備

対象は`TC-OUT-001` / `test-case-design` / `deterministic` / 1 attemptです。実行前に、最終Evaluator/Skill revisionのclean WSL2 checkout、schema 2 profile、固定runtime、ChatGPT login状態、fresh isolation evidence、空のrun output rootを照合します。初回smokeではJudgeを起動しません。`run.py`の実行経路上、Judgeはsemantic suiteでのみ呼び出されます。ただしschema 2 profileではJudge model項目も必要なので、実行しない設定項目についても利用可能なmodel IDが確定するまでprofileを完成させません。

準備する実行条件：

- Codex CLI/runtime：上記0.163.0と照合済みdigest
- profile：schema 2、`wsl2-dual-bubblewrap`、ChatGPT login固定
- Agent timeout：900秒、1 attempt
- Judge：初回deterministic smokeでは起動しない
- output root：`.agent-eval-runs/TC-OUT-001-chatgpt-smoke-<final-SHA>`
- Agent/Judge modelとreasoning effort：未選択。利用可能性を確認していないmodel IDは指定しない
- 固定revision：この変更を含むcommit SHAをEvaluator/Skill revisionとして使う

実行commandの形は次のとおりです。profileのAgent/Judge modelとreasoning effort、およびrevisionを確定し、fresh isolation evidenceを検証した後に限り利用できます。

```bash
python -m scripts.skills.evals.agent.run \
  --suite deterministic \
  --skill test-case-design \
  --eval-id TC-OUT-001 \
  --skill-revision <final-40-character-SHA> \
  --execution-profile .agent-eval-runs/config/profile.json \
  --output-root .agent-eval-runs/TC-OUT-001-chatgpt-smoke-<final-SHA> \
  --repeat 1 \
  --agent-name codex \
  --agent-model <account-confirmed-model-ID> \
  --agent-command codex
```

smoke後は1 attemptの保存結果、graderの判定、Agent/Repair cleanup状態、実行前後manifest、認証方式分類、evidenceの検証状態を確認します。redacted応答、実行/cleanup失敗、未確認evidenceは成功扱いしません。

## 7. モデル利用可能性と未確定事項

`codex login status`は認証方式を示しますが、ChatGPT plan、workspace設定、rollout、現在の利用枠や選択可能modelを確定しません。OpenAIの案内でもCodexのmodel/利用枠はplanやworkspace条件に依存します。固定CLIのmodel catalogにIDが存在することだけでは、このアカウントでの利用可能性を確認できません。そのためAgent/Judge model IDとreasoning effortを埋めたprofileは作成していません。

初回smokeはユーザー指定どおり追加課金・API Key・追加creditsなしを前提にします。現在のChatGPT利用枠の残量は取得していません。最終的な利用可能modelをアカウントのCodex model selectorで確認できるまで、smokeは実行不可です。

## 8. 後続評価の順序

初回smoke成功後は一括実行せず、`TCN-OUT-001`、`TC-SEM-001`、`WF-SEM-003`を個別に進めます。その後、固定QTS target `84ce165493649550832731a60cf436f8ae29c56b`の独立2 attempt、Judge fixture検証、Skill改善候補、独立回帰の順で準備します。Judge fixture 11件（人間レビュー9件、決定論的レビュー2件）は未承認のまま維持し、承認を代行しません。改善候補は自動採用しません。

## 9. 実Agent/API評価の状態

この作業では認証状態確認と合成テストのみを行いました。実認証を伴うAgent/Judge、実モデル応答、API/model requestは実行していません。ChatGPT利用枠の購入・追加、課金情報登録、API Key発行もしていません。

参考：Codex利用条件は[OpenAI Help Center: ChatGPT Work and Codex](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex)、固定CLIの認証status実装は[Codex CLI 0.163.0 source](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/login.rs)を参照しました。
