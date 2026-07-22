---
id: plm_bom_structural_integrity
category: ssot
enforcement: advisory
---

# PLM｜BOM 結構完整性（語意）

## 目的
產品生命週期管理（PLM）的核心是物料清單（BOM）。BOM 表達「產品由哪些
料件、以什麼數量、什麼層級組成」。BOM 的結構正確性無法只靠欄位規則判斷，
需要理解父子關係、層級與用量的語意是否自洽。

## 適用情境
任何承載 BOM、料件組成、產品結構的資料表（如 bom、bom_item、
product_structure、part_usage 等）。

## 違反後果
BOM 結構若有循環引用、缺漏父階、用量語意不清，會導致成本展開、
需求展開（MRP）錯誤。但這類問題需語意判斷，故設為**只提示**。

## 卡控
```check-llm
這是與 PLM 物料清單（BOM）相關的 schema。請從產品結構語意檢視：
- 是否有清楚表達父件與子件的關係（parent / child 或 assembly / component）？
- 是否有用量（quantity）欄位，且其語意明確（每單位父件所需子件數量）？
- 父子關係是否可能形成循環引用（A 包含 B、B 又包含 A）的風險？
- BOM 是否與「版次 / 有效日期」綁定，能表達同一產品不同版本的組成差異？
針對每個疑慮，指出相關的表或欄位，以「給設計者思考的提問」語氣描述。
```
