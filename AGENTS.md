# Agent 操作規範

這是 ClickHouse DDL 資料治理工具。完整使用方式見 `README.md`；新增規則時再讀
`SKILL_AUTHORING.md`。

## 驗證 DDL

使用者要求驗證、產生報告或跑檢查時：

```bash
.venv/bin/python run.py
```

新 DDL 放在 `input/<名稱>.sql`。同名 companions：

- `.sample.json`：樣本資料
- `.context.txt`：業務情境
- `.domains.yaml`：要載入的 domain
- `.keys.yaml`：明確 Business Key
- `.lineage.yaml`：來源、目標與欄位映射

`Common` 永遠載入；其他 domain 只由 `.domains.yaml` 指定。不得把 ClickHouse
`ORDER BY` 或 `PRIMARY KEY` 當成 Business Key。外部 lineage 來源必須存在於已選
domain 的 `production/`；沒有 YAML 時只能把推測稱為建議，不能說成已確認血緣。

## 補完顧問區

未設定本地 LLM 時，`run.py` 產生 Markdown、JSON 與
`reports/<名稱>.advisory_prompt.md`，但不產 HTML。Agent 應：

1. 讀取 `advisory_prompt.md`。
2. 依其中格式產生 `reports/<名稱>.advisory_result.json`。
3. 執行 `.venv/bin/python merge_advisory.py`。
4. 呈現完成的 `.report.md`；需要分享時提供 `.report.html`。

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
3. 規則只放 `config/skills/` 或 `config/skills_py/`，引擎只提供機制。
4. `run.py` 是唯一日常入口；預設掃 `input/`，可用 `DATAVAL_INPUT_DIR` 切換範例。
5. 改動後執行 checking verbs、architecture、golden 三組測試；只有刻意改變結果時才
   使用 `tests/golden_test.py --update`。
