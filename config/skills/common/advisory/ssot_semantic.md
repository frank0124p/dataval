---
id: ssot_semantic
category: ssot
enforcement: advisory
---

# SSOT 候選衝突偵測（語意）

## 目的
registry 尚未涵蓋的權威衝突、跨域重複事實、模糊 join key，需要語意判斷來提名候選。

## 適用情境
新 data subject 引入跨域 join 時。

## 違反後果
非硬性錯誤。只提示，經人工確認後沉澱進 registry。

## 卡控
```check-llm
請檢視 schema：(1) 看似有多個權威擁有者的實體 (2) 跨域重複儲存的同一事實
(3) 可能不指向同一實體的模糊 join key。
對每個發現指出表或欄位，以「給設計者思考的提問」語氣描述。
```
