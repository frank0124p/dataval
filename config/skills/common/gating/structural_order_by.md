---
id: structural_order_by
category: structural
enforcement: blocking
---

# 表必須有 ORDER BY（ClickHouse）

## 目的
MergeTree 家族依 ORDER BY 建立稀疏索引，缺少它等於放棄索引。

## 適用情境
所有 ClickHouse 資料表。

## 違反後果
大表查詢將全表掃描，效能崩潰。故會擋。

## 卡控
```check
require: has_order_by
```
