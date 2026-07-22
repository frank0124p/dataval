---
id: scm_grn_needs_po
category: structural
enforcement: blocking
---

# 收貨單必須掛採購單號

## 目的

收貨單沒有採購單號,收貨無法對回採購,三方對帳(採購/收貨/付款)斷裂。

## 適用情境

表名含 goods_receipt 的收貨單表。

## 違反後果

收了什麼、憑什麼收無從稽核,付款依據不完整。

## 修正建議

補上 po_no 欄位,值對應採購單的單號。

## 卡控

```check
applies_to: name_matches ".*goods_receipt.*"
require: has_column po_no
```
