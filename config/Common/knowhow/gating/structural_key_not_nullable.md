---
id: structural_key_not_nullable
category: structural
enforcement: blocking
---

# 鍵欄位不可為 Nullable

## 目的
主鍵／排序鍵為 Nullable 會破壞合併與去重語意，並帶來額外標記欄位開銷。

## 適用情境
所有含鍵的資料表。

## 違反後果
合併、去重與比較行為不可靠。故會擋。

## 卡控
```check
require: no_nullable_in_key
```
