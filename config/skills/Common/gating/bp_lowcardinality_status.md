---
id: bp_lowcardinality_status
category: best_practice
enforcement: blocking
---

# status 欄位須用 LowCardinality（ClickHouse）

## 目的
低基數高重複欄位以 LowCardinality 儲存可大幅省空間與記憶體。

## 適用情境
含 status 欄位的表。

## 違反後果
儲存與查詢成本浪費。故會擋。

## 卡控
```check
require: lowcardinality_when_present status
```
