# Reference

logical primary（TC）は1件でPASS、attemptは2件でFAIL 1件・PASS 1件と、単位を分けて報告する。attemptの件数をlogical primaryの分母へ加算せず、異なる単位をまたぐ合計やPASS率を出さない。初回FAILの記録は消さず、retry履歴として保持する。
