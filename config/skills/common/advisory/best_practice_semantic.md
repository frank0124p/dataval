---
id: best_practice_semantic
category: best_practice
enforcement: advisory
---

# 依表型態的最佳實踐建議（語意）

## 目的
不同型態的表（交易、維度、事件、PII 存放）各有適用的業界實踐，判斷「這是哪種表、
該套哪些實踐」需要理解。發現若反覆出現，應畢業沉澱成確定性規則。

## 適用情境
每張表，依其表面用途。

## 違反後果
非硬性錯誤。只提示。

## 卡控
```check-llm
判斷每張表的型態（transactional / dimension / event / bridge / PII store 等），
列出真正適用的業界最佳實踐並評估是否符合。
對每個發現指出表或欄位，以「給設計者思考的提問」語氣描述。
```
