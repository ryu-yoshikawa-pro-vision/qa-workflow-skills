# Reference

spec ambiguityは`question-analysis` / 必要時`spec-analysis`へ戻します。原因をRegression Skillが再判定せず、Defectを自動登録しません。修正後current TCが有効ならanalysis / designを無用に再実行せず既存execution Skillで修正確認し、周辺Regressionは別Run目的として計画します。
