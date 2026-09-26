# Eval Input
注文APIのOpenAPI 3.0.3 request schemaを`schema_pointer=#/components/schemas/OrderRequest`、`context=request`として処理する。既存EP/BVA childは`EP-ORDER` / `BVA-ORDER`。

```json
{
  "openapi": "3.0.3",
  "components": {
    "schemas": {
      "OrderRequest": {
        "type": "object",
        "required": ["status", "amount", "customer", "serverId", "credential", "code"],
        "properties": {
          "status": {"type": "string", "enum": ["new", "confirmed"], "nullable": true},
          "amount": {"type": "integer", "minimum": 0, "maximum": 99},
          "customer": {"$ref": "#/components/schemas/Customer", "type": "string"},
          "serverId": {"type": "string", "readOnly": true},
          "credential": {"type": "string", "writeOnly": true},
          "code": {"type": "string", "pattern": "^[A-Z]+$"}
        }
      },
      "Customer": {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}}
      }
    }
  }
}
```

schema adapterから採用済みEP/BVA childへskeletonを渡す。
