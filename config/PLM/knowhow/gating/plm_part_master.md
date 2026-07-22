---
id: plm_part_master_baseline
category: structural
enforcement: blocking
---

# PLM｜料件主檔基線

## 目的
PLM 的料件主檔（part master）是所有產品結構的根。它必須具備穩定的
料號識別與版次欄位，否則無法支撐 BOM 引用與版本追溯。

## 適用情境
料件主檔相關表（表名含 part / item / material）。

## 違反後果
缺少料號或版次會使 BOM 無法正確引用、版本無法追溯，是 PLM 的根本錯誤，
故設為**會擋**。

## 卡控
```check
applies_to: name_matches ".*(part|item|material).*"
require: has_column part_no
require: has_column revision
```
