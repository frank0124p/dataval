---
id: <唯一代號_小寫英數底線>
category: <structural | naming | best_practice | ssot>
enforcement: <blocking | warning>
---

# <規範標題>

## 目的
<這條在治理什麼、為何重要。會被帶進報告當理由。>

## 適用情境
<什麼樣的表/欄位適用。>

## 違反後果
<違反了會造成什麼問題，以及為何設成這個 enforcement 等級。>

## 修正建議
<選填：違反時的具體修法。留空則由卡控動詞自動生成。>

## 卡控
```check
# applies_to 選填（限定適用範圍），可省略：
# applies_to: name_matches "<表名正則>"
# 以下擇需要的動詞，可多條（完整清單見 SKILL_AUTHORING.md 第 3 節）：
require: has_column <欄位>
# require: column_type <欄位> <型別>
# require: not_nullable <欄位>
# require: has_order_by
# require: engine_matches MergeTree
# require: type_not_used Float
```
