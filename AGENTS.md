# Agent 操作規範

這是 ClickHouse DDL 資料治理工具。完整使用方式見 `README.md`；新增規則時再讀
`SKILL_AUTHORING.md`。

## 驗證 DDL

使用者要求驗證、產生報告或跑檢查時：

```bash
.venv/bin/python run.py
```

新 DDL 放在 `input/<名稱>.sql`；`input/` 不放其他設定。同一個名稱的治理資訊集中在
`config/cases/<名稱>.yaml`，可包含 `sample_data`、`context`、`domains`、
`business_keys` 與 `lineage`。

同名 Mermaid ER diagram 放在 `config/er_diagrams/<名稱>.mmd`。ER 關係只能轉成
lineage 顧問候選；case config 沒有 `lineage` 明確宣告時，不得把 ER association 說成已確認
的資料流向。

`Common` 永遠載入；其他 domain 只由 case config 的 `domains` 指定。不得把 ClickHouse
`ORDER BY` 或 `PRIMARY KEY` 當成 Business Key。外部 lineage 來源必須存在於已選
domain 的 `production/`；沒有 YAML 時只能把推測稱為建議，不能說成已確認血緣。

## 補完顧問區

未設定本地 LLM 時，`run.py` 仍會產生 Markdown、JSON、HTML 與
`reports/<名稱>.advisory_prompt.md`；HTML 會清楚標示語意規則待補完。需要補完時 Agent 應：

1. 讀取 `advisory_prompt.md`。
2. 依其中格式產生 `reports/<名稱>.advisory_result.json`。
3. 執行 `.venv/bin/python merge_advisory.py`。
4. 確認更新後的 `.report.html`，閘門結果必須不變。

顧問建議一律是 `info`，永遠不能改變合規判定。合併程式會逐項比較合併前後的
gating findings，不一致就拒絕寫入。

## 新增規則

```bash
.venv/bin/python rules.py new <rule_id>
.venv/bin/python rules.py check
.venv/bin/python run.py
```

指定 domain／區域時使用：

```bash
.venv/bin/python rules.py new <domain> <gating|advisory> <rule_id>
```

規則格式、允許的 checking verbs 與檢查清單以 `SKILL_AUTHORING.md` 為準。

## 不可破壞的保證

1. 閘門只用確定性規則；LLM 只能進顧問區。
2. 同一 DDL＋規則集，checking rule ID 結果必須一致。
3. DDL 個案設定放 `config/cases/`；Domain skills 放 `config/domain/`；Python 規則放
   `config/rules/`；Mermaid ER diagram 放 `config/er_diagrams/`。引擎只提供機制。
4. `run.py` 是唯一日常入口；預設掃 `input/`，可用 `DATAVAL_INPUT_DIR` 切換範例。
5. 改動後執行 checking verbs、architecture、golden 三組測試；只有刻意改變結果時才
   使用 `tests/golden_test.py --update`。
