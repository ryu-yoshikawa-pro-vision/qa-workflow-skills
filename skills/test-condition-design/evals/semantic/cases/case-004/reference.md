# 判定根拠
`SPEC-CRUD-001`にあるentity × `order-lifecycle` × CRUD operationの各matrix cellをcompleteness itemとして具体化する。`not_applicable`もAuthority付きで保持する。consistencyは`place → amend → cancel` sequence後のOrder=`cancelled`、InventoryReservation=全量release、BillingBalance=place前残高というpostconditionを別基準・itemとして表す。具体的なentity・function・operation・sequence後状態を対応づける。
