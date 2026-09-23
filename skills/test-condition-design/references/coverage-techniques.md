# カバレッジ技法 詳細規則

このリファレンスは、`test-condition-design`で具体的なテスト技法を採用した場合に読みます。採用しない技法のために読む必要はありません。

テスト技法固有のカバレッジ基準 / カバレッジ項目規則は、このSkill内では本ファイルを正本とします。

## 同値分割

適用条件: 複数値が同じ挙動になると判断できる場合。

1. 仕様から意味の異なる有効 / 無効パーティション候補を先に識別する
2. 対象範囲内の各パーティションを原則1つ以上カバーする
3. 採用しないパーティションは扱いと理由を残す

## 境界値分析

適用条件: 順序付け可能な値で、挙動が境界で変わる場合。

- 通常は2-value BVAを既定とする
- 境界実装リスクが高い、過去不具合がある、境界ロジックが複雑、または境界両側の差をより強く確認する必要がある場合は3-value BVAを使う
- 2-valueでは、各境界について境界値と隣接パーティション側の最も近い値をカバレッジ項目にする
- 3-valueでは、各境界について境界値とその両側の最も近い値をカバレッジ項目にする
- 値の最小刻み / 精度が仕様やデータ型から決められない場合は、架空の「±1」を作らない
- 最小 / 最大のどちらを扱うかは仕様上存在する境界に従う

例: 上限100で整数の場合、2-valueは100 / 101、3-valueは99 / 100 / 101。

採用方式と具体的なカバレッジ項目を明示し、未定義境界を創作しません。

## デシジョンテーブル

適用条件: 複数条件の組合せで結果が決まり、列挙漏れや矛盾が起きやすい場合。

1. 条件と結果から実行可能ルール候補を識別する
2. 実行可能な各ルールを原則カバレッジ項目とする
3. 成立しない組合せは`成立不能`として根拠を残す。成立不能assignmentは制約の証跡として保持し、実行可能ルールやCoverage Itemとして採番・列挙せず、coverage母集団にも含めない。表で追跡する必要がある場合は、rule / Coverage Itemとは別の制約欄へ置き、期待actionを付けない
4. ルールを削減する場合は妥当な扱いと理由を残す

## 状態遷移

適用条件: 現在状態とイベントで挙動が変わる場合。

1. 対象範囲内の仕様上の状態と有効遷移候補を先に識別する
2. 既定のカバレッジ基準は**対象範囲内の全有効遷移カバレッジ**とする
3. 各有効遷移をカバレッジ項目として追跡する
4. 対象範囲から除外する状態 / 有効遷移は扱いと理由を残す
5. 無効遷移は仕様、プロダクトリスク、過去不具合等の根拠があるものだけ追加する

全無効遷移を機械生成しません。案件で別のカバレッジ基準が明示されている場合はそちらを優先します。

## Pairwise / 組合せ

適用条件: 複数の独立軸があり、全組合せが大きすぎ、相互作用リスクが説明できる場合。

- 因子 / 値候補と制約を先に明示する
- Pairwiseと表現する場合は、成立可能な全値ペアが少なくとも1つの生成済みカバレッジ項目へ含まれることを、ツール出力または明示的なペアカバレッジ確認で検証できること
- 制約で成立しないペアは`成立不能`として根拠を残す
- 因子 / 値 / 制約、生成カバレッジ項目、2-wiseカバレッジ確認根拠を追跡できる形で残す

全2-wiseカバレッジを確認できない場合はPairwiseと呼ばず「代表組合せ」と表現します。カバレッジ項目からテストケースへの展開は`test-case-design`へ委ねます。

## Domain Testing

多変数境界を扱う場合は、scalar BVAと区別してReliable Domain Coverageを使います。

- partition全体を構成するborderと、その内側を示すrelationを明示する
- closed / open border、`=`、`!=`のそれぞれに必要なON / OFF / IN / OUT pointを識別する
- `<= / >=`のclosed borderはON=border上、OFF=raw relationがfalseになる1 step外、IN=raw relationがtrueになる1 step内、OUT=OFFからさらに1 step外とする。`< / >`のopen borderはOFF=border上、ON=raw relationがtrueになる1 step内、IN=ONからさらに1 step内、OUT=raw relationがfalseになる点とする。`=`はONと両側OFF、`!=`はOFFと両側ONを扱う
- pointは全partition expressionへ再代入して所属を確認し、対象border以外を跨いだ点を対象borderのcoverageとして数えない
- 有限decimalから厳密に表せないrequired pointを丸めて作らない。`unrepresentable_point`等のunsupportedとして残す
- required pointを構成できない場合は基準を下げず、partition / anchor / step等の不足を未解決として示す
- borderごとに別のconditionを作り、quantityとpriceのような変数を一つの曖昧な境界へまとめない。入力で確定できるanchor、relation、stepを使い、未確定のborderは必要parameterごとに止める

## CRUD Testing

CRUDの**completeness**と**consistency**を別々に閉じます。

- completenessでは明示されたentity / function / operation matrixの候補を扱い、missing operationは欠陥と断定せず、Authority付き`not_applicable`または確認事項へ閉じる
- consistencyでは業務意味が明示されたoperation sequenceを別に扱い、sequence中のoperation、entity、functionをmatrixへ解決する
- consistency sequenceが未正規化、またはmissing operationが未処置ならCRUD全体をcompleteとしない
- 未提示の副作用、順序、禁止operation、CRUDセルを創作しない
- completeness itemは`entity × function × operation`の具体cellを示す。業務操作だけではCRUD operationとのmappingを推測しない
- consistency criterionは指定sequenceを実行した後の状態関係を示す。cell対応を列挙しただけで業務状態の一貫性を確認したとはしない

## Classification Tree / 組合せ

- classification adapterはfactor / class skeletonとstable identityを採番済みcombinatorial childへ渡す。adapter自身をexecution CIにしない
- factor値、constraints、strength別subsetが不足する場合も判明済みskeletonを保持し、未確定parameterを明示してchild completionを保留する
- constraintsを適用した後のfeasible tuple集合をstrengthごとに作り、その全件をcoverage基準とする。limitや不足値を理由にstrengthを下げない
- 生成row、required tuple、covered tupleを区別し、重複する意味上の組合せを作らない

## State Transition / Flow

- 有効state / transition候補と、その範囲内で採用するtransition、round-trip、n-switch等のsequence基準を区別して示す
- 各sequenceは開始state、必要なsetup prefix、coverage sequence、各transitionのfrom / event / toを追跡可能にする
- 指定された初期stateからsequenceの先頭transitionへ到達する経路が必要なら、その有効transition列を`setup_prefix`として含める。n-switchのwindowが途中stateから始まる場合も、window開始stateを初期stateとみなさない
- round-tripは同じ開始stateへ戻る経路として確認し、n-switchと置き換えない
- setup不能またはguardが未確定のrequired transitionを母集団から黙って除外しない

## Grammar / Syntax-Based Testing

- GrammarはAuthorityで定義されたproductionと制約だけを対象にする
- production reachabilityを確認し、到達不能productionも扱いと根拠を残す
- mutation candidateや構文解析候補を、Authorityが定めていない製品上のinvalid入力と断定しない
- grammar / production / error classificationに必要な意味情報が足りなければ候補と未解決事項を残し、入力を創作しない

## Schema / UI

- JSON Schema 2020-12、OpenAPI 3.0、HTML controlは別々の意味規則で処理する。同名keywordだけでsemanticsを共有しない
- enum、range、required等からEP / BVA / combinatorial skeletonとschema由来test data requirementを作る場合は、同じschema runtimeの再実行結果にある`derived.test_data_requirements`を使う。現在のschema runtime resultがある場合は、そのfieldと`unsupported_items`、`derived_child_inputs`をそのまま使い、別builderや説明文から再構成しない
- schemaの`required`は、coverage観点ではsource schemaにあるproperty名とcontextを保った必須存在条件として表し、各該当propertyをpresence itemへ具体化する。local `$ref`で解決されたschema内のrequired propertyも含め、Reference Object siblingや未解決referenceから制約を作らない。runtimeが返した`derived.test_data_requirements`はそのまま保持する。requirement rowにsource pointerがない場合、順序やhashから個別rowとpropertyの対応を推測せず、schema上確認できる必須条件とrow単位の対応不能を区別して記す
- schemaのCoverage Itemには各required propertyのpathとpresence条件を個別に記録し、coverage候補の説明だけで終えない。nullableとenumの制約が交差して作るinvalid候補も、property path・typed candidate・invalid理由を別itemとして明示する。derived child skeleton / TDRへ存在しないitemを追加せず、runtimeのhash identityへ未提供のsource対応を割り当てない
- OpenAPI requestでは`readOnly`をrequired / request test dataから除外し、responseでは`writeOnly`をrequired / expected responseから除外する。nullable、Reference Object、`$ref` siblingsもOpenAPI 3.0契約で判断する
- OpenAPI `nullable=true`はschema typeのnull許容を候補として保持し、required / enum等の他constraintと区別してnull caseの扱いを明示する
- OpenAPI 3.0では`nullable=true`がbase typeへnullを加えるが、enum等の他constraintは維持される。nullがenumにない場合は、typed `null`の具体的なinvalid Coverage Itemとenum外である理由を明示し、runtime skeletonや`derived.test_data_requirements`へ追加しない。`derived.test_data_requirements`はschema runtimeが実際に出した要求だけを使う
- unsupported keywordは影響するsubtreeへ限定し、独立して評価できるproperty / itemを継続する
- UI patternはcurrent `ui_pattern_candidates.py` runtime resultの`static_data_versions.ui_pattern_catalog`とcatalog version、canonical `pattern_key`、候補の全`candidate_key`を保持してalias解決を示す。catalog候補は製品Authorityや期待結果ではない。catalogにないpatternや未対応constraintを推測せずunsupportedとして残し、disabled / readonlyの意味をconstraintへ誤変換しない。HTML control typeのconstraint subsetは`schema_cases.py`側の責務

## Test Data Requirements / Materialization

- scalar equality、finite enum、integer / decimal / date / fixed-offset datetime range、version range、booleanのtyped valueを保持する
- model-wide requirementは同じsource modelのcurrent targetsへ適用し、target-specific requirementはcurrent target version refsに指定されたtargetだけへ適用する
- 同じcurrent target上でmodel-wide requirementと当該targetを参照するtarget-specific requirementを合わせ、同じdimensionのintersectionを行う。互換性のない要求や安全に扱えないoperatorを隠さない。適用対象が異なるtarget同士はcross-intersectしない
- `applicable_target_refs`はcurrent target集合から再導出する。保存値がある場合は再導出結果との完全一致を確認し、source target versionが古い場合はcurrentとして受理しない
- 複数targetをCIへmergeするとき、また複数CIをTCへまとめるときは、同時成立するrequirement unionへ同じintersection規則を再適用する。merge unionのintersectionがconflict / unsupportedなら統合を拒否し、merged CIを作らない。conflictという注記だけでmerge候補を有効扱いしない
- CI groupingは同一TCN、model、current target version、execution、expected result rootを満たす候補に限る。どの単位のcompletionを確認したか明示する
- merge候補のpredicate適用とrequirement unionの検証はmaterialization処理であり、製品behaviorを検査するtest techniqueと混同しない

## Random Testing

- deterministic generationではfixed seed、distribution、`case_count`を入力として確定し、`pcg32-v1` runtime resultから同じ値列を再現する。seedやdistributionの説明だけで生成済みとは扱わず、現在resultの値列をcoverage itemへ保持する
- completionは`required_case_count = case_count`と生成件数の一致で判断する。Random Testingに一般的な仕様Coverage 100%を付与しない
- Randomの件数完了を境界 / partition / pair等のspecification coverage完了と同一視しない。明示されたsystematic criterionがある場合は別coverageとして保持する
- 値域、case count、seed等の必須parameterがない場合に適当な値を作らない

## Metamorphic Testing

- relation、source input、全follow-upとtransform列、expected relationを明示し、各executionを自己完結させる
- required pair数は`source_inputs数 × follow_ups数`、generated pair数は実際に作成したexecutionとして区別する
- runtime resultがある場合は`required_pairs / generated_pairs / complete`をそのresultから記録し、実際に生成されたpairをcoverage itemへ対応づける。全required pairがmaterializeされた場合だけgenerator completionとする。relationを一度使ったことを全input coverageと呼ばない
- productへ妥当なrelation、source集合、transform、expected relationはAuthorityとともに正規化し、oracleを創作しない

## エラー推測

過去不具合、実装複雑性、既知のプラットフォーム挙動、ドメイン固有の失敗等の根拠がある場合に使います。

カバレッジ基準は**選択した失敗仮説を検証すること**です。技法全体の完全網羅とは表現せず、採用仮説と根拠を残します。

## シナリオ / ユースケース

業務フローや複数画面・状態をまたぐ意味のある経路を確認する場合に使います。

1. 仕様上の主経路、代替経路、例外経路候補を識別する
2. 主経路をカバーする
3. 仕様またはプロダクトリスク上必要な代替 / 例外経路をカバーする
4. 採用しない経路は扱いと理由を残す

## 技法横断の禁止事項

- 技法名が書かれているだけでカバレッジ済みとしない
- プロダクトリスクから未定義の期待挙動を創作しない
- 候補母集団を識別せず「重要なものだけ」を恣意的に採用しない
- 低プロダクトリスクだけを理由に対象候補を無言削除しない
- テストケースの実行手順へ先回りしない

## runtime generatorとの対応

runtime generatorは、この文書の技法規則を機械的に適用できる範囲だけをsupported subsetとして扱います。入力が範囲外、制約が矛盾、期待挙動の根拠がない場合は、適当な代表値・ルール・遷移を創作せず、`unsupported`または`unresolved`とその理由を返します。生成したstable ID、選択条件、coverage item、semantic itemは、同じModel Keyとgeneration fingerprintで追跡し、`test-case-design`が実行手順を追加するまでケース完了とはみなしません。
