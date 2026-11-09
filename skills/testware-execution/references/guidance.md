# 非E2E実行・診断ガイダンス

## 起点と方式

- ブラウザE2Eはe2e-test-execution、browser直接TC操作はtest-execution。API-only Playwright Test、Vitest、component、batch、event、非機能、許可された静的解析ツールは本Skill。
- 永続testwareの作成・更新はtestware-implementation。今回は実行のみなら作成を前提にしない。
- 永続testwareなしの非ブラウザTCでは、Given/When/Thenに相当する開始状態・操作・期待結果・観測方法・cleanupを事前固定する。実操作やraw結果から期待値を作り直さない。
- 仕様Authority、非機能閾値、測定条件が欠ければ該当判定は未確定とする。既存専門SkillのUI/UX、WCAG判定を非機能の一般合格として転用しない。

## Preflightと実runner

1. 対象repoとcommit、TCまたは明示testware ref、必要run、build、対象環境・権限、実行入口chain、設定、fixture/hook、データ準備・依存先を確認する。
2. scriptやpackage managerの入口とpre/post chainを読み、runner管理setup/teardownとrun外の準備・cleanupを区別する。静的解析も外部I/O・ファイル変更・秘密情報に関する権限を確認する。
3. 副作用はscope単位で最大回数とcleanupを記録する。実行状態不明のattemptも起こり得る副作用を消費したものとし、未確認なら再実行しない。共有資源のreservationは実providerのreadbackが必須で、単なるフラグやoperation claimでは代用できない。
4. 実runnerを開始したことをprocess/API等の証拠で確定し、runner stdout、machine-readable reporter、開始/終了、timeout、exit code、attemptをその実run refへ結び付ける。artifactの鮮度を検査し、旧runを採用しない。
5. reporterを自動変換して元runner statusを書き換えない。cleanup失敗は元のテストFAILへ書き換えず、対象runの安全な完了を別に制限する。

## Vitestの識別と完全性

- 固定source commit、repo相対path、suite／title path、実効filterと選択集合で個別testを照合する。ファイル移動や改名、同じtitle、パラメータ化testでは旧版へ自動対応しない。
- contract.reconcile_vitest()はVitest JSON reporterの選択項目との集合照合を補助する。reporter中の絶対pathは検証済みrepo rootからの相対pathへ呼出元が安全に正規化する。単にpathを切り詰めない。
- selection_verifiedは実コマンドと列挙完全性の証拠があるときだけtrueとする。重複名の解決不能、missing、unplanned、partial selectionは全件取得・全PASSとしない。
- retry/attemptをJSON reporterが提供しない場合、attemptの取得完全性は不明と記録する。1件の最終statusを複数attemptへ捏造しない。raw passedはassertion品質やTC合格を証明しない。
- Vitestのtest-control境界を一般HTTP APIの受入証拠に使わない。独立HTTP fixtureと実製品の結果を分けて保管する。

## 直接観測・静的解析・診断

- 直接観測は各期待結果の実観測値・不一致・観測不能を保存する。HTTP 200でも本文が異なればFAIL。必要な副作用を観測できなければ判定不能。最初の実操作前に停止なら未実行。
- 静的解析は適用ルール/設定、対象ファイル、実ツールversion、raw出力、取得件数・未解析範囲を記録する。意味レビューの誤検出・仕様矛盾はadversarial-reviewに渡す。
- 診断はSUT/testware/fixture/environment/runner/仕様不明を原因候補とし、観測事実、仮説、反証、確度、次のownerを記録する。元runの判定と欠陥候補は分離する。
- 実装しただけのtestwareや独立fixtureのPASSは実製品runの証拠ではない。

## 下流の引継ぎ

H/Jが読む単位はrun ref＋source/build/testware revision、個別test path/title、任意の元TC ref、実効選択条件、attempt、raw evidence、取得完全性、cleanup、診断とする。保存providerのreadback revisionや承認はAの正式公開契約に従い、未接続ならblockedとする。A〜J成果物の実参照をつないだ全体受入はPR #22で行う。
