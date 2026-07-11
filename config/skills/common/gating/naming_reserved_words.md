---
id: naming_reserved_words
category: naming
enforcement: warning
---

# 欄位名避免 SQL 保留字

## 目的
使用保留字當欄名需要跳脫，易出錯。

## 適用情境
所有欄位。

## 違反後果
查詢撰寫易踩雷。設為警告。

## 卡控
```check
require: columns_not_named select,from,where,table,order,group,index,key,all
```
