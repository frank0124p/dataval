---
id: naming_columns_commented
category: naming
enforcement: blocking
---

# 所有欄位必須有 COMMENT 註解

## 目的
欄位註解是資料字典的最小單位，中介資料平台會直接讀取。

## 適用情境
所有欄位。

## 違反後果
缺註解使語意只能口耳相傳。故會擋。

## 卡控
```check
require: all_columns_commented
```
