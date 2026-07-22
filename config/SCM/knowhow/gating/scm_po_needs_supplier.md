---
id: scm_po_needs_supplier
category: structural
enforcement: warning
---

# 採購單必須掛供應商(範例)

## 目的
採購單沒有供應商編號,付款與對帳無從追溯。

## 適用情境
表名含 purchase_order 的表。

## 違反後果
採購與付款斷鏈。

## 修正建議
補 supplier_no 欄位。

## 卡控

```check
applies_to: name_matches ".*purchase_order.*"
require: has_column supplier_no
```
