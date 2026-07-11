# 顧問區補完任務（給 opencode agent）

Python 端沒有 LLM 連線，以下顧問區項目需要你用你的 LLM 完成。
顧問區一律**只提示、永不影響合規判定**。請用繁體中文，措辭為「給設計者思考的提問」，不要下結論。

## 你要做的事

1. 依下方 schema 與情境，針對這三個面向產生建議：
   - **命名語意**：跨表縮寫不一致、同概念異名、欄名與型別語意不符。
   - **主體性概念**：每張表代表的業務主體是否抓對、粒度是否合理、主體間關係建模是否恰當。
   - **各 domain 語意 skill**：見下方 pending_skills 列出的每條，依其描述產生建議。

2. 把結果寫成 JSON 檔：`reports/subscription.advisory_result.json`，格式：
```json
{
  "naming_semantic": [
    {"target": "表或表.欄位", "message": "給設計者的提問", "rationale": "為什麼"}
  ],
  "concept": [
    {"target": "表名", "message": "主體性提問", "rationale": "為什麼"}
  ],
  "skills": {
    "<skill_id>": [
      {"target": "表或欄位", "message": "提問", "rationale": "為什麼"}
    ]
  }
}
```
此檔案必須符合 `config/advisory_result.schema.json`；合併前會強制驗證。

3. 跑一次合併，把建議填進報告與 HTML：
```
python merge_advisory.py
```

完成後 reports/subscription.report.html 的顧問區就會顯示真實建議，而非「待補完」。

## 待補的語意 skill（pending_skills）
### `best_practice_semantic` · common · 依表型態的最佳實踐建議（語意）
判斷每張表的型態（transactional / dimension / event / bridge / PII store 等），
列出真正適用的業界最佳實踐並評估是否符合。
對每個發現指出表或欄位，以「給設計者思考的提問」語氣描述。

### `naming_semantic` · common · 跨表命名語意一致性（語意）
請檢視整個 schema，找出規則無法機械判斷的命名語意問題：
- 縮寫不一致（cust 與 customer 並存）
- 同一概念在不同表使用不同名稱（user_id 與 member_id 指同一實體）
- 欄位名稱與其型別或註解語意不符
對每個發現指出表或欄位，以「給設計者思考的提問」語氣描述。

### `ssot_semantic` · common · SSOT 候選衝突偵測（語意）
請檢視 schema：(1) 看似有多個權威擁有者的實體 (2) 跨域重複儲存的同一事實
(3) 可能不指向同一實體的模糊 join key。
對每個發現指出表或欄位，以「給設計者思考的提問」語氣描述。

## 未登錄主體候選
[
  {
    "entity": "subscription",
    "table": "subscription",
    "evidence": [
      "customer_email",
      "MonthlyPrice",
      "started_at"
    ]
  },
  {
    "entity": "event",
    "table": "billing_event",
    "evidence": [
      "amount",
      "occurred_at"
    ]
  }
]

## schema 與情境
{
  "context": "新增 subscription 主體，跨 CRM 與 billing 兩個 domain",
  "tables": [
    {
      "name": "dim_customer",
      "primary_key": [],
      "sorting_key": [
        "customer_id"
      ],
      "business_key": [
        "customer_id"
      ],
      "business_key_source": "explicit_metadata",
      "columns": [
        {
          "name": "customer_id",
          "type": "int",
          "nullable": false,
          "comment": null
        },
        {
          "name": "customer_name",
          "type": "string",
          "nullable": false,
          "comment": null
        },
        {
          "name": "customer_email",
          "type": "string",
          "nullable": false,
          "comment": null
        },
        {
          "name": "customer_tier",
          "type": "string",
          "nullable": false,
          "comment": null
        },
        {
          "name": "created_at",
          "type": "datetime",
          "nullable": false,
          "comment": null
        },
        {
          "name": "updated_at",
          "type": "datetime",
          "nullable": false,
          "comment": null
        }
      ]
    },
    {
      "name": "subscription",
      "primary_key": [],
      "sorting_key": [
        "subscription_id"
      ],
      "business_key": [
        "subscription_id"
      ],
      "business_key_source": "explicit_metadata",
      "columns": [
        {
          "name": "subscription_id",
          "type": "int",
          "nullable": false,
          "comment": null
        },
        {
          "name": "customer_id",
          "type": "string",
          "nullable": false,
          "comment": null
        },
        {
          "name": "customer_email",
          "type": "string",
          "nullable": false,
          "comment": null
        },
        {
          "name": "MonthlyPrice",
          "type": "float",
          "nullable": false,
          "comment": null
        },
        {
          "name": "started_at",
          "type": "datetime",
          "nullable": false,
          "comment": null
        },
        {
          "name": "created_at",
          "type": "datetime",
          "nullable": false,
          "comment": null
        }
      ]
    },
    {
      "name": "billing_event",
      "primary_key": [],
      "sorting_key": [
        "event_id"
      ],
      "business_key": [
        "event_id"
      ],
      "business_key_source": "explicit_metadata",
      "columns": [
        {
          "name": "event_id",
          "type": "int",
          "nullable": false,
          "comment": null
        },
        {
          "name": "customer_id",
          "type": "int",
          "nullable": false,
          "comment": null
        },
        {
          "name": "amount",
          "type": "float",
          "nullable": false,
          "comment": null
        },
        {
          "name": "occurred_at",
          "type": "datetime",
          "nullable": false,
          "comment": null
        }
      ]
    }
  ]
}
