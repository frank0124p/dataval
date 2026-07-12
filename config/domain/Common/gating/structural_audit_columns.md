---
id: structural_audit_columns
category: structural
enforcement: warning
---

# 表應有稽核欄位（created_at / updated_at）

## 目的
稽核欄位支撐血緣追蹤與變更歷史。

## 適用情境
所有資料表。

## 違反後果
缺少稽核欄位使變更不可追溯。設為警告。

## 卡控
```check
require: has_column created_at
require: has_column updated_at
```
