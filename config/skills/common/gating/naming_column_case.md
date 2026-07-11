---
id: naming_column_case
category: naming
enforcement: blocking
---

# 欄位名須為 snake_case 全小寫

## 目的
欄位命名樣式一致是資料字典與自動化的基礎。

## 適用情境
所有欄位。

## 違反後果
不一致的欄名增加理解成本與 join 錯誤風險。故會擋。

## 卡控
```check
require: all_columns_name_match [a-z][a-z0-9_]*
```
