# Semantic contract: Evaluation scope closure

The selected top-level scope must close every row as issue confirmed, no issue, undetermined, or out of scope with a reason. In the production helper schema, `判定不能` is the canonical status for an undetermined row; it counts as closed when its reason is supplied. Blank selected rows cannot be reported complete. Only script-generated fixed rows and closure are authoritative.
