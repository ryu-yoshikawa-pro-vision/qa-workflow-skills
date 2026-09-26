# 判定根拠
relation label、source input、各follow-up input、expected relationを自己完結したexecutionへ含める。1 relationを1回生成しただけで十分とはせず、runtime resultの`required_pairs`と`generated_pairs`、`complete`を区別し、生成されたpairごとにCoverage Itemへ対応づけて完了判定する。
