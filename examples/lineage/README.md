# Lineage 可執行範例

這組資料刻意涵蓋七種結果。從專案根目錄執行：

```bash
DATAVAL_INPUT_DIR=examples/lineage/input \
DATAVAL_REPORT_DIR=examples/lineage/reports \
.venv/bin/python run.py
```

完成後查看 `examples/lineage/reports/*.report.html`：

| 範例 | 預期 lineage 結果 |
|---|---|
| `01_declared_valid` | 外部 CRM production 來源、欄位與型別全部通過。 |
| `02_declared_type_mismatch` | `LINEAGE.TYPE_COMPATIBILITY` 擋下 String ← UInt64。 |
| `03_local_cycle` | `LINEAGE.CYCLE` 擋下 local A ↔ B 循環。 |
| `04_inferred_relationship` | 沒有 YAML；依 Business Key 產生顧問區候選。 |
| `05_no_relationship_found` | 沒有 YAML，也沒有可靠關係；建議明確設定 `upstream: []`。 |
| `06_standalone_declared` | 已明確宣告無上游，lineage 閘門全部通過。 |
| `07_er_diagram_suggestion` | case config 沒有 lineage；從同名 Mermaid ER diagram 產生顧問建議。 |

`examples/lineage/input/` 只放七份 DDL；各案例的 context、domains、Business Key、
lineage 與 sample data 都集中在 `config/_engine/cases/<案例名>.yaml`。第 07 案例的
ER diagram 位於 `config/_engine/er_diagrams/07_er_diagram_suggestion.mmd`。

這些案例包含刻意失敗的設計，因此示範時不要加 `--strict`。
