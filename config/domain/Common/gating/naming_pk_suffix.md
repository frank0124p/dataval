---
id: naming_pk_suffix
category: naming
enforcement: warning
---

# 主鍵欄位建議以 _id 結尾

## 目的
可預測的鍵名（x_id）讓 join 推斷與理解更容易。

## 適用情境
所有主鍵欄位（純 id 亦可）。

## 違反後果
鍵名不可預測增加 join 成本。設為警告。

## 卡控
```check
require: pk_ends_with _id
```
