---
id: plm_bom_needs_quantity
category: structural
enforcement: blocking
---

# PLM｜BOM 必須記錄用量

## 目的
BOM 表達產品由哪些子件組成，若缺少用量欄位，無法展開物料需求與成本。

## 適用情境
BOM／產品結構相關表（表名含 bom）。

## 違反後果
缺少用量會使 MRP 與成本展開錯誤。屬料件結構的根本資訊，故會擋。

## 卡控
```check
applies_to: name_matches ".*bom.*"
require: has_column quantity
```
