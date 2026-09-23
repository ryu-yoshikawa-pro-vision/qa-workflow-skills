# Eval Input
## 変更
設定ファイルの小さなDSLへ新しいproductionと、構文エラーを検出するmutationを追加する。
このDSLは本番サービスの起動設定に使われる。設定を誤って受理すると全利用者の起動が阻害され、復旧には設定のrollbackが必要になる。
変更は独立した単一productionの追加で、関連grammar依存や分岐追加は示されていない。対象parserについて過去不具合や不安定性の情報はない。
## 目的
Syntax-Based Testingの採用可否と、品質上の重点領域を決める。
