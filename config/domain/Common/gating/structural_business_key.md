---
id: structural_business_key
category: structural
enforcement: blocking
---

# 表必須有 Business Key

## 目的
每張表需要穩定的業務識別鍵，才能被正確引用、合併與去重。
ClickHouse ORDER BY 只是物理排序鍵，不等於業務唯一性。

## 適用情境
所有資料表。

## 違反後果
無 business key 的表無法可靠識別一筆資料。故會擋。

## 卡控
```check
require: has_business_key
```
