---
id: crm_baseline
category: structural
enforcement: warning
---

# CRM 領域基線（範例佔位，請以實際 CRM 規範替換）

## 目的

示範 CRM 領域規則檔的放置位置與格式；此範例僅要求客戶主檔具備稽核欄位，
上線前應替換為真實領域規範。

## 適用情境

表名含 customer 的主檔表（範例條件，依實際規範替換）。

## 違反後果

缺稽核欄位時，客戶主檔變更無法追溯。

## 卡控

```check
applies_to: name_matches ".*customer.*"
require: has_column updated_at
```
