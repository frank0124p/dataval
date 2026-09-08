# Claude Code 入口

**先完整讀 `AGENTS.md`——那是權威規範，本檔只是速查卡。**
架構與使用方式見 `README.md`；新增或修改規則時才需要 `SKILL_AUTHORING.md`。
第一次接觸這包程式碼的人請看 `QUICKSTART.md`。

這是 ClickHouse DDL 資料治理工具：吃使用者寫的 DDL ＋ 關聯 ＋ 語意描述，
輸出「這個設計合不合規、為什麼、怎麼修」的報告。

## 環境

一律用 `.venv/bin/python`，不要用系統 python。

```bash
python -m venv .venv && .venv/bin/pip install -e .   # 首次
```

## 交報告 = 跑完三步，缺一不可

使用者說「檢查 input／跑檢查／產生報告」都是要一份**完整報告**＝
閘門區 ＋ **已補完的顧問區**。

```bash
.venv/bin/python run.py [subject]            # ① 閘門區（零 LLM）＋ advisory_prompt
# ② run.py 印出「⚠️ 顧問區尚未補完」時，你要用自身 LLM 讀
#    govern_doc/<名>/<名>.advisory_prompt.md，產出 <名>.advisory_result.json
.venv/bin/python merge_advisory.py           # ③ 合併並重繪三式報告
.venv/bin/python merge_advisory.py --status  # 驗收：exit 0 = 全數補完
```

**跳過 ②③ 就交報告 = 交了半份**（HTML 顧問區只會顯示「待補完」）。
使用者指定了 subject 就只跑那一個，不要全掃 `input/`。

## 兩種模式（run.py 自動判定，互斥）

| | 觸發條件 | 你要做什麼 |
|---|---|---|
| 🎨 design | subject 只有 `context.md`，還沒有 `<名>.sql` | 讀 `design_prompt.md` → 產 `design_result.json` → 重跑 |
| 🛡 govern | 有 `<名>.sql` | 上面的三步流程 |

## 五條不可破壞的保證

1. **閘門只用確定性規則；LLM 只能進顧問區**——顧問建議一律 `info`、永不擋。
2. 同一 DDL ＋ 同一規則集，checking rule ID 結果必須一致（報告位元組穩定）。
3. **不得代寫使用者的權威輸入**——`input/<名>/<名>.sql`、`relations.yaml`、
   `context.md` 是使用者的。缺件就轉告使用者補，不要自己填。
4. **不得自行把問答的 `proposed` 改成 `answered`**——代填答案要由使用者驗證。
5. `run.py` 與 `merge_advisory.py` **不連網**。外部平台資料走
   `datahub_fetch.py` 抓成 snapshot，判定只讀 snapshot。

## 檔案該放哪（速查）

```text
input/<名>/          使用者權威輸入：<名>.sql、relations.yaml、context.md（三件必備）
                     選填：samples/、answers.yaml、derivation.sql、datahub.yaml
config/<域>/         領域知識：knowhow（規則）／naming／ssot／erd／flows／business
config/_engine/      引擎層設定（不放規則）
production/<域>/     已核准上線的主體——設計新表前先問「是不是有人做過了」
design_doc/<名>/     🎨 設計產出        govern_doc/<名>/  🛡 治理產出
build/ rules_history/ iterations/       自動生成，勿手改
```

改 `config/` 時**只修格式不動語意內容**；規則檔的格式由
`config_format.py` 起跑前自動補齊。

## 測試

```bash
.venv/bin/python -m unittest discover -s tests -p '*_test.py'
```

改動後三組必跑：checking verbs、architecture、golden。
**只有刻意改變規則結果時**才用 `tests/golden_test.py --update` 重建基準。
