---
id: bp_datetime_timezone
category: best_practice
enforcement: warning
---

# DateTime 應標明時區

## 目的
時區不明的時間在跨區情境無法正確比較，應以 DateTime('UTC') 或註解標明。

## 適用情境
所有 DateTime 欄位。

## 違反後果
跨區比較與換算出錯。設為警告。

## 卡控
```check
require: datetime_with_timezone
```
