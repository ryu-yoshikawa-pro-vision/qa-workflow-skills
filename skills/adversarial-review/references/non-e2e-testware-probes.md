# 非E2E testware・製品静的テストの独立レビュー

## 非E2E testwareの検証

- 正本はTC／TCN／CI等の現在有効な根拠、またはTCなしの明示testware対象と採用基準。testwareコード自身を仕様根拠にしない。
- 期待結果ごとに、具体的なassertionの位置、観測する対象・タイミング、使用するfixture・mock、誤陽性になり得る前提を対応付ける。
- assertion不在、常に真となる条件、自己生成データとの同値比較だけの検証、誤った期待値、必要分岐の不足を反証する。
- 仕様やrunner結果を取得できない場合は該当観点を判定不能とする。raw PASSやcoverage-analysisのTC閉鎖性で独立品質レビューを代替しない。
- 実装ownerの説明から期待値を推測して補完しない。重大な不一致がある場合、品質ゲート未完了とし元runのstatusは保持する。

## 静的な要求・設計・コードレビュー

- 要求書／設計書／対象差分／コードのsource refとrevision・取得完全性、適用する規則・Authorityを受け取る。正式TCやtestwareの作成を必須としない。
- 要求の矛盾、設計の条件欠落、コードの規則不一致をsource位置・根拠・影響とともに示す。見つけていない欠陥や存在しないルールを作らない。
- 誤検出候補、根拠不足、未取得範囲、修正後revisionでの再レビューを区別する。
- toolによる静的解析はtestware-executionがraw evidenceを保存し、その意味解釈が必要な範囲のみ本Skillで独立レビューする。
- 製品コード／仕様変更・Issue正式登録は行わず、各owner／defect-managementに引き継ぐ。
