---
id: naming_table_snake_case
category: naming
enforcement: blocking
---

# 表名須為 snake_case 全小寫

## 目的
一致的表名讓資產可預測、可被工具處理。

## 適用情境
所有資料表。

## 違反後果
大小寫混用造成跨工具相容問題。故會擋。

## 卡控
```check
require: table_name_matches [a-z][a-z0-9_]*
```
