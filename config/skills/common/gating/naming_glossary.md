---
id: naming_glossary
category: naming
enforcement: warning
---

# 命名對照詞彙字典

## 目的
欄位命名應使用公司認可的標準詞，避免縮寫與同義異名造成理解成本與整合困難。
此規則對照 config/glossary.yaml 的詞彙字典做檢查，比寫一堆正則更易維護。

## 適用情境
所有資料表的欄位命名。

## 違反後果
使用禁用縮寫（如 cust、qty）或非標準別名（如 client、goods）會降低資料可讀性與
跨系統一致性。設為警告，提醒改用標準詞。

## 卡控
```check
require: no_banned_term
require: no_alias_term
```
