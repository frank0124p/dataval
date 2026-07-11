---
id: naming_identifier_length
category: naming
enforcement: warning
---

# 識別字長度不超過 64 字元

## 目的
過長的表名／欄名不利閱讀與部分工具相容。

## 適用情境
所有表名與欄名。

## 違反後果
可讀性下降。設為警告。

## 卡控
```check
require: identifier_max_length 64
```
