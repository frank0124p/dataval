---
id: bp_no_float
category: best_practice
enforcement: blocking
---

# 不可使用 Float 型別

## 目的
Float 不適合需要精確比較與彙總的數值。

## 適用情境
所有欄位（以 ClickHouse 為主）。

## 違反後果
累積捨入誤差造成靜默錯誤。故會擋。

## 卡控
```check
require: type_not_used Float
```
