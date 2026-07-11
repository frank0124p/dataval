---
id: bp_money_decimal
category: best_practice
enforcement: blocking
---

# 金額欄位必須用 Decimal

## 目的
名稱含 amount/price/cost/fee 等的金額欄位，使用浮點數會導致對帳不平。

## 適用情境
所有金額類欄位。

## 違反後果
捨入誤差在彙總時放大且難追查。故會擋。

## 卡控
```check
require: type_not_for_matching .*(amount|price|cost|balance|fee|revenue|salary).* float
```
