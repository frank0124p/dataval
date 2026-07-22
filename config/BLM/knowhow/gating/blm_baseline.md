---
id: blm_baseline
category: structural
enforcement: warning
---

# BLM 領域基線(範例佔位,請以實際 BLM 規範替換)

## 目的

示範 BLM 領域規則檔的放置位置與格式;此範例僅要求主檔具備稽核欄位,
上線前應替換為真實領域規範。

## 適用情境

表名含 blm 的主檔表(範例條件,依實際規範替換)。

## 違反後果

缺稽核欄位時,主檔變更無法追溯。

## 卡控

```check
applies_to: name_matches ".*blm.*"
require: has_column updated_at
```
