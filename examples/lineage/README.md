# Lineage 可執行範例

這組資料刻意涵蓋六種結果。從專案根目錄執行：

```bash
DATAVAL_INPUT_DIR=examples/lineage/input \
DATAVAL_REPORT_DIR=examples/lineage/reports \
.venv/bin/python run.py
```

完成後查看 `examples/lineage/reports/*.report.md`：

| 範例 | 預期 lineage 結果 |
|---|---|
| `01_declared_valid` | 外部 CRM production 來源、欄位與型別全部通過。 |
| `02_declared_type_mismatch` | `LINEAGE.TYPE_COMPATIBILITY` 擋下 String ← UInt64。 |
| `03_local_cycle` | `LINEAGE.CYCLE` 擋下 local A ↔ B 循環。 |
| `04_inferred_relationship` | 沒有 YAML；依 Business Key 產生顧問區候選。 |
| `05_no_relationship_found` | 沒有 YAML，也沒有可靠關係；建議明確設定 `upstream: []`。 |
| `06_standalone_declared` | 已明確宣告無上游，lineage 閘門全部通過。 |

每個案例都有 `.sample.json` 與 `.keys.yaml`。有外部 CRM 來源的案例另外附
`.domains.yaml`；需要明確關係的案例附 `.lineage.yaml`。

這些案例包含刻意失敗的設計，因此示範時不要加 `--strict`。
