# Eval Input
`SPEC-CRUD-001`が次のentity × function × operation matrixを定義する。functionは`order-lifecycle`。

| Entity | create | read | update | delete |
| --- | --- | --- | --- | --- |
| Order | `place` | `get` | `amend`, `cancel` | not_applicable |
| InventoryReservation | `reserve` | not_applicable | `adjust` | `release` |
| BillingBalance | not_applicable | `get` | `charge`, `adjust`, `refund` | not_applicable |

同Authorityはsequence `place → amend → cancel` とpostconditionを定義する: Orderはcancelled、InventoryReservationは全量release済み、BillingBalanceはplace前の残高へ戻る。各cell・sequence・postconditionはこのAuthorityに基づく。CRUD Coverage Itemを作る。
