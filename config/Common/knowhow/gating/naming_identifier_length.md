---
id: naming_identifier_length
category: naming
enforcement: blocking
---

# 表名不超過 64、欄名不超過 48 字元

## 目的
過長的表名／欄名不利閱讀、跨工具相容與下游引用。
表名上限 64 字元、欄位名上限 48 字元，超過即擋。

## 適用情境
所有表名與欄名。

## 違反後果
可讀性與相容性問題會擴散到所有下游。設為會擋。

## 卡控
```check
require: table_name_max_length 64
require: column_name_max_length 48
```
