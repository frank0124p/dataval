# dataval — ClickHouse 資料設計治理

把一組資料設計（DDL ＋ 表間關聯 ＋ 語意描述）丟進來，它告訴你
**合不合規、為什麼、怎麼修**——輸出 Markdown / JSON / HTML 三式報告。

一句話原則：**判定用確定性規則，LLM 只給建議。** 同一份輸入永遠得到同一個
判定結果，不會今天過明天不過。

| 想做什麼 | 看哪裡 |
|---|---|
| 第一次用，5 分鐘跑出第一份報告 | [`QUICKSTART.md`](QUICKSTART.md) |
| **日常怎麼用** | 這一頁 |
| 輸入檔案的格式與慣例 | [`input/README.md`](input/README.md) |
| 架構、規則系統、內部機制、設計理由 | [`TECHNICAL.md`](TECHNICAL.md) |
| 自己寫規則 | [`SKILL_AUTHORING.md`](SKILL_AUTHORING.md) |

---

## 安裝

需要 Python 3.10 以上。

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

要逐版完全一致的依賴：`.venv/bin/pip install -r requirements.lock`
再 `.venv/bin/pip install -e . --no-deps`。

---

## 放檔案：一個主題一個資料夾

```text
input/
  order/                  ← 資料夾名 = 主題名
    order.sql             DDL（檔名要跟資料夾同名）          ← 必備
    relations.yaml        表怎麼接（from / to / cardinality）← 必備
    context.md            這是什麼、粒度、用途、上下游        ← 必備
    samples/<表名>.csv     樣本資料，一張表一份               ← 選填
```

**三件必備缺一不可**——缺了不會產報告，會告訴你缺什麼。樣本沒有也能跑，
只是樣本相關的檢查會略過。

還有四件選填，需要時再加（格式見 [`input/README.md`](input/README.md)）：

| 檔案 | 什麼時候要 |
|---|---|
| `answers.yaml` | 迭代問答的答案（工具自動產生，你只要填答案） |
| `derivation.sql` | 寬表主題：實際的 Join SQL，拿來三方對照 |
| `datahub.yaml` | 平台上的表名跟這裡不一樣時，指定去 DataHub 哪裡拿 |
| `<表名>.sql` | DDL 想一表一檔拆開放（同資料夾的 `.sql` 會一起載入） |

repo 附兩個範例：`input/order/`（合格的完整參考）與
`input/subscription/`（刻意含違規的示範）。

---

## 跑起來

```bash
.venv/bin/python run.py            # 跑 input/ 下所有主題
.venv/bin/python run.py order      # 只跑指定主題（可多個）
```

**如果 console 印出「⚠️ 顧問區尚未補完」**，代表報告只完成一半——確定性
判定好了，但語意建議還沒補。請 AI agent（Claude Code / opencode）接手：

```
「幫我補完顧問區」
```

它會讀 `advisory_prompt.md`、產出建議，再跑 `merge_advisory.py` 合回報告。
接了本機 LLM（設 `DATAVAL_LLM_BASE_URL`）就不用這一步。

**如果印的是「♻️ 顧問區可沿用」**，代表 input 與判定結果都沒變，上次的建議
仍然成立——不用再跑一次 LLM，直接 `python merge_advisory.py` 就完成了。

**Exit code**：`0` 全過 · `1` 有不合規（加 `--strict` 時）· `2` 有主題輸入不齊。

---

## 看報告

```text
govern_doc/order/
  order.report.html       ← 雙擊就開，先看這個
  order.report.md         人讀版
  order.report.json       程式讀版
  order.subject_summary.md 這個主題在做什麼（晉升正式區前的說明）
  order.precheck.md       輸入缺件時看這份
```

HTML 報告最上面是判定卡片（合規／不合規、被哪幾條規則擋下），往下逐項列出
每個檢查的**期望、實際、怎麼修、依據來自哪個檔案**。可搜尋、可只看
fail/warning。

報告分兩區，看的時候要分清楚：

| 區 | 誰產生 | 會不會擋 |
|---|---|---|
| **閘門區** | 確定性規則，零 LLM | **會**——合規判定只由這區決定 |
| **顧問區** | LLM 的語意建議 | **不會**，一律只是提示 |

---

## 只有想法、還沒有 DDL？

`input/<名>/` 裡只放 `context.md`、不放 `.sql`，`run.py` 就切換成
**🎨 設計模式**：從語意描述反過來幫你設計出邏輯設計、實體設計與草稿 DDL，
產物在 `design_doc/<名>/`（包含一份 `etl.yaml` ETL 設定建議檔）。

設計稿滿意後，把 `design.sql` 存成 `input/<名>/<名>.sql`，同一個主題就自動
轉成 🛡 治理模式。細節見 [`TECHNICAL.md`](TECHNICAL.md) 的「兩種模式」。

---

## 問答迭代：報告會問你問題

報告不只給結論，還會把「工具判斷不了、需要你交代」的事變成問題，寫進
`input/<名>/answers.yaml`：

```yaml
answers:
  - id: SSOT.AUTHORITY@customer_name
    question: customer_name 在本主題與 CRM 都出現，哪邊是權威？
    answer: CRM 是權威，本表只是快照冗餘。
    status: proposed        # ← 改成 answered 就算數
```

`proposed` 是 AI **代填的草稿答案**，需要你確認：同意就改 `answered`
（答案可以改），不想追就改 `deferred`。改完重跑，工具會帶著你的答案進下一輪，
不再重問。全部問題都答完 ＋ 閘門全過 = **收斂**。

---

## 其他指令

| 指令 | 做什麼 |
|---|---|
| `python promote.py <名>` | 合規的主題晉升到 `production/`（正式區） |
| `python production_audit.py` | 正式區全區健檢（斷鏈、循環、規則版本過期） |
| `python rules.py new <域> gating <id>` | 新增一條規則 |
| `python rules.py list` | 看目前有哪些規則 |
| `python config_index.py` | 產生 config 知識庫總索引 |
| `python datahub_fetch.py` | 抓 DataHub 中介資料（唯一會連網的指令） |
| `python config_format.py --check` | 檢查 config 格式（run.py 起跑前會自動修） |

---

## 卡住了？

| 狀況 | 怎麼辦 |
|---|---|
| 說「缺件」不產報告 | 看 `govern_doc/<名>/<名>.precheck.md`，缺什麼補什麼 |
| 報告顧問區寫「待補完」 | 跟 AI agent 說「幫我補完顧問區」 |
| 不懂某條規則在檢查什麼 | 規則就是 `config/<領域>/knowhow/` 下的 Markdown，打開就能讀 |
| DataHub 那區全是「⏭ 待接 API」 | 正常，不影響判定。接上平台後填 `config/_engine/datahub.yaml` |
| 想知道判定為什麼是這樣 | 報告每一項都寫了「依據來自哪個檔案」 |

---

## 跑測試

```bash
.venv/bin/python -m unittest discover -s tests -p '*_test.py'
```

改過規則後如果 golden 測試紅了，確認是**刻意**改變結果才用
`python tests/golden_test.py --update` 重建基準。
