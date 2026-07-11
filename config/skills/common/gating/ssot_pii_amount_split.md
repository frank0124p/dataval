---
id: ssot_pii_amount_split
category: ssot
enforcement: warning
---

# 個資與金額應分表存放

## 目的
PII 與金額混存使權限難分級、真實源歸屬模糊。

## 適用情境
同時可能出現個資與金額的表。

## 違反後果
權限與 SSOT 邊界模糊。設為警告，由設計者判斷。

## 卡控
```check
require: columns_not_both customer_email MonthlyPrice
```
