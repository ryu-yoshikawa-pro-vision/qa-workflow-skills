# Coverage Techniques 詳細規則

このreferenceは、`test-condition-design`で具体的なテスト技法を採用した場合に読みます。採用しない技法のために読む必要はありません。

テスト技法固有のCoverage Criteria / Coverage Item規則はこのSkill内では本ファイルをSingle Source of Truthとします。

## 同値分割

適用条件: 複数値が同じ挙動になると判断できる場合。

1. 仕様から意味の異なる有効 / 無効Partition候補を先に識別する
2. 対象範囲内の各Partitionを原則1つ以上カバーする
3. 採用しないPartitionはDispositionと理由を残す

## 境界値分析

適用条件: 順序付け可能な値で、挙動が境界で変わる場合。

- 通常は2-value BVAを既定とする
- 境界実装Riskが高い、過去不具合がある、境界ロジックが複雑、または境界両側の差をより強く確認する必要がある場合は3-value BVAを使う
- 2-valueでは、各境界について境界値と隣接Partition側の最も近い値をCoverage Itemにする
- 3-valueでは、各境界について境界値とその両側の最も近い値をCoverage Itemにする
- 値の最小刻み / 精度が仕様やデータ型から決められない場合は、架空の「±1」を作らない
- 最小 / 最大のどちらを扱うかは仕様上存在する境界に従う

例: 上限100で整数の場合、2-valueは100 / 101、3-valueは99 / 100 / 101。

採用方式と具体Coverage Itemを明示し、未定義境界を創作しません。

## Decision Table

適用条件: 複数条件の組合せで結果が決まり、列挙漏れや矛盾が起きやすい場合。

1. 条件と結果から実行可能ルール候補を識別する
2. 実行可能な各ルールを原則Coverage Itemとする
3. 成立しない組合せは`成立不能`として根拠を残す
4. ルールを削減する場合は妥当なDispositionと理由を残す

## 状態遷移

適用条件: 現在状態とイベントで挙動が変わる場合。

1. 対象範囲内の仕様上の状態と有効遷移候補を先に識別する
2. 既定Coverage Criteriaは**対象範囲内の全有効遷移Coverage**とする
3. 各有効遷移をCoverage Itemとして追跡する
4. 対象範囲から除外する状態 / 有効遷移はDispositionと理由を残す
5. 無効遷移は仕様、Product Risk、過去不具合等の根拠があるものだけ追加する

全無効遷移を機械生成しません。案件で別のCoverage Criteriaが明示されている場合はそちらを優先します。

## Pairwise / 組合せ

適用条件: 複数の独立軸があり、全組合せが大きすぎ、相互作用Riskが説明できる場合。

- Factor / Value候補とConstraintを先に明示する
- Pairwiseと表現する場合は、成立可能な全Value Pairが少なくとも1つの生成済みCoverage Itemへ含まれることを、tool出力または明示的なPair Coverage確認で検証できること
- Constraintで成立しないPairは`成立不能`として根拠を残す
- Factor / Value / Constraint、生成Coverage Item、2-wise Coverage確認根拠を追跡できる形で残す

全2-wise Coverageを確認できない場合はPairwiseと呼ばず「代表組合せ」と表現します。Coverage ItemからTest Caseへの展開は`test-case-design`へ委ねます。

## Error Guessing

過去不具合、実装複雑性、既知platform挙動、domain固有失敗等の根拠がある場合に使います。

Coverage Criteriaは**選択した失敗仮説を検証すること**です。技法全体の完全網羅とは表現せず、採用仮説と根拠を残します。

## Scenario / Use Case

業務フローや複数画面・状態をまたぐ意味のある経路を確認する場合に使います。

1. 仕様上の主経路、代替経路、例外経路候補を識別する
2. 主経路をカバーする
3. 仕様またはProduct Risk上必要な代替 / 例外経路をカバーする
4. 採用しない経路はDispositionと理由を残す

## 技法横断の禁止事項

- 技法名が書かれているだけでCoverage済みとしない
- Product Riskから未定義の期待挙動を創作しない
- 候補母集団を識別せず「重要なものだけ」を恣意的に採用しない
- 低Product Riskだけを理由に対象候補を無言削除しない
- Test Caseの実行手順へ先回りしない
