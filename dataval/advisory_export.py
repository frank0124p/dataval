"""顧問區補完橋接。

run.py 是獨立子程序、不繼承 opencode 的 LLM，所以「需要 LLM 的顧問區檢查」
在 Python 端只會標成「待補完」。本模組產出一份給 agent 的指示 + 結構化待補清單，
agent 用它自己的 LLM 產生建議、寫成 <名>.advisory_result.json，再跑一次
`python merge_advisory.py` 把結果合併進報告（含 HTML）。

流程：
  run.py           → reports/<名>.report.{md,json}（確定性檢查結果）
                   → reports/<名>.advisory_prompt.md（給 agent 的指示＋schema）
  agent（用 LLM）  → reports/<名>.advisory_result.json（產生的建議）
  merge_advisory   → 重繪 HTML/MD/JSON，顧問區填入真實建議
"""
from __future__ import annotations
import json
import re
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
此檔案必須符合 `config/_engine/advisory_result.schema.json`；合併前會強制驗證。

3. 跑一次合併，把建議填進報告與 HTML：
```
python merge_advisory.py
```

完成後 reports/{name}.report.html 的顧問區就會顯示真實建議，而非「待補完」。

4. 合併後會產出 `reports/{name}.answers_draft.yaml`（本輪待答問題骨架）。
   請為其中每題 open question 填入 `suggested_answer`（依 context 與 schema
   推測的最合理答案，繁體中文）與 `suggested_kind`（semantic＝只澄清語意；
   structural＝需要改 DDL／relations／context 權威輸入，此時一併填
   `suggested_applied_to`）。

5. **在對話中逐題向使用者提問**（標準回答路徑）：把每題連同建議答案呈給
   使用者，使用者在 command line 回答（接受／修改／擱置）後，把**使用者的
   回答**代筆回寫進 `input/{name}/answers.yaml`（id／question 照草稿帶入；
   擱置記 `status: deferred`）。每一筆回寫都必須出自使用者的明確回覆——
   不得自行編造、不得未經回覆就把 suggested_answer 當成已答；structural
   答案的權威輸入修改仍由使用者手動進行。最後回報本輪狀態
   （第幾輪、待答幾題、閘門 fail 幾項、是否收斂）。

## 已澄清事項（使用者已回答，勿重複提問）
{clarified}

（產生建議時，上列主題不得再以任何措辭重問；可基於答案深化**新的**面向。）

## 待補的語意 skill（pending_skills）
{pending_skills}

## 未登錄主體候選
{unregistered_candidates}

## schema 與情境
{schema_json}
"""


def build_advisory_prompt(schema: Schema, context: str,
                          name: str = "", pending_skills: list | None = None,
                          unregistered_candidates: list | None = None,
                          clarified: str = "") -> str:
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
    ps_txt = "\n\n".join(
        f"### `{s['id']}` · {s.get('domain', 'Common')} · {s['title']}\n"
        f"{s['desc']}" for s in ps) or "（無）"
    return _INSTRUCTIONS.format(
        name=name or "<名>",
        clarified=clarified or "（無——本輪尚無已回答的問題）",
        pending_skills=ps_txt,
        unregistered_candidates=json.dumps(
            unregistered_candidates or [], ensure_ascii=False, indent=2),
        schema_json=json.dumps(payload, ensure_ascii=False, indent=2))


def validate_advisory_result(result) -> list[str]:
    """Validate the advisory payload against advisory_result.schema.json semantics.

    Kept dependency-free so the offline governance path remains runnable.
    """
    errors: list[str] = []
    if not isinstance(result, dict):
        return ["最外層必須是 JSON object"]
    required = {"naming_semantic", "concept", "skills"}
    missing = required - set(result)
    extra = set(result) - required
    if missing:
        errors.append(f"缺少必要欄位：{sorted(missing)}")
    if extra:
        errors.append(f"不允許的欄位：{sorted(extra)}")

    def validate_suggestions(value, path):
        if not isinstance(value, list):
            errors.append(f"{path} 必須是 array")
            return
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_path} 必須是 object")
                continue
            expected = {"target", "message", "rationale"}
            if set(item) != expected:
                errors.append(f"{item_path} 欄位必須剛好是 {sorted(expected)}")
            for key in expected:
                if not isinstance(item.get(key), str) or not item.get(key, "").strip():
                    errors.append(f"{item_path}.{key} 必須是非空字串")

    if "naming_semantic" in result:
        validate_suggestions(result["naming_semantic"], "naming_semantic")
    if "concept" in result:
        validate_suggestions(result["concept"], "concept")
    skills = result.get("skills")
    if skills is not None:
        if not isinstance(skills, dict):
            errors.append("skills 必須是 object")
        else:
            for skill_id, suggestions in skills.items():
                if not re.fullmatch(r"[a-z][a-z0-9_]*", str(skill_id)):
                    errors.append(f"skills rule id 無效：{skill_id}")
                validate_suggestions(suggestions, f"skills.{skill_id}")
    return errors
