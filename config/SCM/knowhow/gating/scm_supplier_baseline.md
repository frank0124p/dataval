---
id: scm_supplier_baseline
category: structural
enforcement: blocking
---

# 供應商主檔基線(範例,依實際 SCM 規範替換)

## 目的

供應商主檔是採購與付款流程的根,必須有穩定的供應商編號才能被
採購單、對帳與付款引用。

## 適用情境

表名含 supplier / vendor 的主檔表。

## 違反後果

採購單無法可靠對應供應商,對帳與付款追溯斷裂。

## 修正建議

補上 supplier_no 欄位作為業務識別。

## 卡控

```check
applies_to: name_matches ".*(supplier|vendor).*"
require: has_column supplier_no
```
