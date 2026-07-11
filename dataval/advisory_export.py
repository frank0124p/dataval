"""顧問區補完橋接。

run.py 是獨立子程序、不繼承 opencode 的 LLM，所以「需要 LLM 的顧問區檢查」
在 Python 端只會標成「待補完」。本模組產出一份給 agent 的指示 + 結構化待補清單，
agent 用它自己的 LLM 產生建議、寫成 <名>.advisory_result.json，再跑一次
`python merge_advisory.py` 把結果合併進報告（含 HTML）。

流程：
  run.py           → reports/<名>.report.html（顧問區標「待補完」）
                   → reports/<名>.advisory_prompt.md（給 agent 的指示＋schema）
  agent（用 LLM）  → reports/<名>.advisory_result.json（產生的建議）
  merge_advisory   → 重繪 HTML/MD，顧問區填入真實建議
"""
from __future__ import annotations
import json
from .model import Schema

_INSTRUCTIONS = """\
# 顧問區補完任務（給 opencode agent）

Python 端沒有 LLM 連線，以下顧問區項目需要你用你的 LLM 完成。
顧問區一律**只提示、永不影響合規判定**。請用繁體中文，措辭為「給設計者思考的提問」，不要下結論。

## 你要做的事

1. 依下方 schema 與情境，針對這三個面向產生建議：
   - **命名語意**：跨表縮寫不一致、同概念異名、欄名與型別語意不符。
   - **主體性概念**：每張表代表的業務主體是否抓對、粒度是否合理、主體間關係建模是否恰當。
   - **各 domain 語意 skill**：見下方 pending_skills 列出的每條，依其描述產生建議。

2. 把結果寫成 JSON 檔：`reports/{name}.advisory_result.json`，格式：
```json
{{
  "naming_semantic": [
    {{"target": "表或表.欄位", "message": "給設計者的提問", "rationale": "為什麼"}}
  ],
  "concept": [
    {{"target": "表名", "message": "主體性提問", "rationale": "為什麼"}}
  ],
  "skills": {{
    "<skill_id>": [
      {{"target": "表或欄位", "message": "提問", "rationale": "為什麼"}}
    ]
  }}
}}
```

3. 跑一次合併，把建議填進報告與 HTML：
```
python merge_advisory.py
```

完成後 reports/{name}.report.html 的顧問區就會顯示真實建議，而非「待補完」。

## 待補的語意 skill（pending_skills）
{pending_skills}

## schema 與情境
{schema_json}
"""


def build_advisory_prompt(schema: Schema, context: str,
                          name: str = "", pending_skills: list | None = None) -> str:
    payload = {
        "context": context,
        "tables": [
            {
                "name": t.name,
                "primary_key": t.primary_key,
                "sorting_key": t.sorting_key,
                "business_key": t.business_key,
                "business_key_source": t.business_key_source,
                "columns": [
                    {"name": c.name, "type": c.base_type,
                     "nullable": c.nullable, "comment": c.comment}
                    for c in t.columns
                ],
            }
            for t in schema.tables
        ],
    }
    ps = pending_skills or []
    ps_txt = "\n".join(f"- `{s['id']}`（{s['title']}）：{s['desc']}" for s in ps) or "（無）"
    return _INSTRUCTIONS.format(
        name=name or "<名>",
        pending_skills=ps_txt,
        schema_json=json.dumps(payload, ensure_ascii=False, indent=2))
