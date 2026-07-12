---
id: structural_engine_mergetree
category: structural
enforcement: blocking
---

# 明細表引擎須為 MergeTree 系列（ClickHouse）

## 目的
明細層資料應使用 MergeTree 家族引擎（MergeTree / ReplacingMergeTree 等）。

## 適用情境
所有明細資料表。

## 違反後果
非 MergeTree 引擎用於明細通常是設計錯誤。故會擋。

## 卡控
```check
require: engine_matches MergeTree
```
