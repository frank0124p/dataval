# 規則草稿生成請求 — scm_grn_needs_po

請依下方 system 指引與需求，直接產出檔案 `drafts/scm_grn_needs_po.md`（只含規則內容本身）。

## system

你是資料治理規則的撰寫助手。請依使用者的需求描述,
產出一條 dataval 規則的 Markdown 檔。嚴格遵守以下格式,只輸出檔案內容本身,
不要任何前後說明或 ``` 包裹:

---
id: scm_grn_needs_po
category: <structural|naming|best_practice|ssot 擇一>
enforcement: <blocking|warning 擇一>
---

# <一句話標題>

## 目的
<為什麼需要這條規則>

## 適用情境
<適用哪些表;若限定表名請說明>

## 違反後果
<不遵守會發生什麼>

## 修正建議
<怎麼改>

## 卡控
```check
<可用動詞(一行一個 require:;applies_to: 可限定表):
 has_column <欄>、column_type <欄> <型>、not_nullable <欄>、
 columns_not_both <欄A> <欄B>、has_primary_key、has_business_key、
 has_order_by、no_nullable_in_key、all_columns_commented、
 column_commented <欄>、engine_matches <pattern>、
 table_name_matches <regex>、all_columns_name_match <regex>、
 type_not_used <型>、type_not_for_matching <名稱regex> <型>、
 lowcardinality_when_present <欄>、datetime_with_timezone、
 identifier_max_length <N>、pk_ends_with <字尾>、
 columns_not_named <a,b,c>、no_banned_term、no_alias_term>
```
若上述動詞表達不了(需跨表比對、需翻樣本資料、需查登記簿),
請不要硬湊;改在檔案最後加一行註解:
<!-- NEEDS_PY: 原因 -->



## 需求

需求描述：收貨單(表名含 goods_receipt)必須有 po_no 欄位,收貨才能對回採購單
