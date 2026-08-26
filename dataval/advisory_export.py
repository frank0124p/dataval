"""顧問區補完橋接。

run.py 是獨立子程序、不繼承 opencode 的 LLM，所以「需要 LLM 的顧問區檢查」
在 Python 端只會標成「待補完」。本模組產出一份給 agent 的指示 + 結構化待補清單，
agent 用它自己的 LLM 產生建議、寫成 <名>.advisory_result.json，再跑一次
`python merge_advisory.py` 把結果合併進報告（含 HTML）。

流程：
  run.py           → govern_doc/<名>/<名>.report.{md,json}（確定性檢查結果）
                   → govern_doc/<名>/<名>.advisory_prompt.md（給 agent 的指示＋schema）
  agent（用 LLM）  → govern_doc/<名>/<名>.advisory_result.json（產生的建議）
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

2. 把結果寫成 JSON 檔：`govern_doc/{name}/{name}.advisory_result.json`，格式：
```json
{{
  "naming_semantic": [
    {{"target": "表或表.欄位", "message": "給設計者的提問", "rationale": "為什麼",
      "proposed_answer": "你代填的建議答案", "proposed_kind": "semantic"}}
  ],
  "concept": [
    {{"target": "表名", "message": "主體性提問", "rationale": "為什麼",
      "proposed_answer": "你代填的建議答案", "proposed_kind": "semantic"}}
  ],
  "skills": {{
    "<skill_id>": [
      {{"target": "表或欄位", "message": "提問", "rationale": "為什麼",
        "proposed_answer": "…", "proposed_kind": "structural",
        "proposed_applied_to": "<名>.sql"}}
    ]
  }}
}}
```
此檔案必須符合 `config/_engine/advisory_result.schema.json`；合併前會強制驗證。

**每題都要附 `proposed_answer`**（依 context 與 schema 推測的最合理答案，
繁體中文）與 `proposed_kind`（semantic＝只澄清語意；structural＝需要修改
DDL／relations／context 權威輸入，此時一併填 `proposed_applied_to`）。
合併時這些代填答案會寫進 `input/{name}/answers.yaml` 標 `status: proposed`
（待驗證）：**不算已答、不餵下一輪 prompt、擋收斂**，直到使用者驗證後
把 status 改成 answered。你不得自行把 proposed 改成 answered——
只有使用者（或使用者在對話中的明確指示）能做這件事。

3. 跑一次合併，把建議填進報告與 HTML：
```
python merge_advisory.py
```

完成後 govern_doc/{name}/{name}.report.html 的顧問區就會顯示真實建議，而非「待補完」。

4. 最後把本輪狀態回報給使用者：第幾輪、待答幾題、**待驗證（代填）幾題**、
   閘門 fail 幾項、是否收斂，並提醒使用者到 `input/{name}/answers.yaml`
   驗證代填答案（把 proposed 改成 answered，答案可修改；不想追的改 deferred）。

## 參考表用途（config erd/tables — input 的新表應正確 reference 這些基準）
{table_purposes}

（判讀方式：對照下列 schema，檢視本次設計是否正確 reference 參考模型——
表的粒度／欄位／關聯偏離文件記載用途時，以提問形式指出。）

## 正式區資產（已核准上線的主體——語意判讀本主體是否該複用）
{production_assets}

（判讀方式：閘門只看得到 relations.yaml 宣告出來的引用；這裡要你用**語意**
判斷——本主體要承載的事實是否已由某個已核准主體承載，即使欄名不同。
判讀結果放進 `skills.production_reuse_semantic`。）

## 已澄清事項（使用者已回答，勿重複提問）
{clarified}

（產生建議時，上列主題不得再以任何措辭重問；可基於答案深化**新的**面向。）

## 衍生 SQL（使用者實際的 Join SQL；引擎已確定性解析）
{derivation}

（判讀方式：對照 schema 與情境，檢視 join 邏輯的**語意**——join 方向與
鍵的選擇是否符合宣稱的粒度、LEFT JOIN 產生的 NULL 語意欄位設計是否有考慮、
運算欄（expression）的業務含義是否清楚。確定性差異——未宣告 join、欄位
缺漏——報告閘門區已列出，**勿重複**；把你的觀察以提問形式融入
naming_semantic／concept／skills 三類即可，不需要新的輸出欄位。）

## 待補的語意 skill（pending_skills）
{pending_skills}

## 未登錄主體候選
{unregistered_candidates}

## schema 與情境
{schema_json}
"""


def _derivation_txt(d: dict | None) -> str:
    """把 engine meta['derivation'] 摘要成 prompt 區塊（無檔案時給占位文字）。"""
    if not d:
        return "（無——本次未提供 derivation.sql）"
    lines = [
        f"檔案：`{d.get('file', 'derivation.sql')}`｜基底表 `{d.get('base_table', '')}`｜"
        f"來源表 {'、'.join(d.get('source_tables', [])) or '（無）'}｜"
        f"join {d.get('join_count', 0)} 組｜輸出 {d.get('output_count', 0)} 欄"
        f"（運算欄 {d.get('expression_count', 0)}）"
    ]
    cov = d.get("coverage")
    if cov:
        lines.append(
            f"與寬表 `{cov.get('wide_table', '')}` 逐欄對照："
            f"對上 {cov.get('covered', 0)}／{cov.get('ddl_columns', 0)} 欄；"
            f"DDL 有但 SQL 沒產出 {cov.get('missing_in_sql') or '（無）'}；"
            f"SQL 產出但 DDL 沒有 {cov.get('extra_in_sql') or '（無）'}")
    matrix = d.get("key_matrix") or []
    if matrix:
        lines.append("")
        lines.append("join 鍵三方對照（✔＝出現）：")
        lines.append("| join 鍵 | 你的 SQL | relations.yaml | 建議 SQL |")
        lines.append("|---|---|---|---|")
        for row in matrix:
            lines.append(
                f"| `{row['pair']}` "
                f"| {'✔' if row.get('in_sql') else '—'} "
                f"| {'✔' if row.get('in_relations') else '—'} "
                f"| {'✔' if row.get('in_proposal') else '—'} |")
    sql = (d.get("sql") or "").strip()
    if sql:
        lines += ["", "```sql", sql, "```"]
    return "\n".join(lines)


def build_advisory_prompt(schema: Schema, context: str,
                          name: str = "", pending_skills: list | None = None,
                          unregistered_candidates: list | None = None,
                          clarified: str = "",
                          table_purposes: dict | None = None,
                          derivation: dict | None = None,
                          production_assets: str = "") -> str:
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
    purposes_txt = "\n".join(
        f"- **{table}**（{ref.get('source', '')}）：{ref.get('purpose', '')}"
        for table, ref in sorted((table_purposes or {}).items())
    ) or "（無——本次的表在參考模型沒有登錄用途）"
    return _INSTRUCTIONS.format(
        name=name or "<名>",
        table_purposes=purposes_txt,
        production_assets=production_assets
        or "（正式區目前是空的——沒有可複用的已核准主體）",
        clarified=clarified or "（無——本輪尚無已回答的問題）",
        derivation=_derivation_txt(derivation),
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
            required = {"target", "message", "rationale"}
            optional = {"proposed_answer", "proposed_kind", "proposed_applied_to"}
            unknown = set(item) - required - optional
            if not required <= set(item) or unknown:
                errors.append(f"{item_path} 欄位必須含 {sorted(required)}，"
                              f"選填限 {sorted(optional)}")
            for key in required:
                if not isinstance(item.get(key), str) or not item.get(key, "").strip():
                    errors.append(f"{item_path}.{key} 必須是非空字串")
            for key in optional & set(item):
                if not isinstance(item.get(key), str):
                    errors.append(f"{item_path}.{key} 必須是字串")
            if item.get("proposed_kind") not in (None, "", "semantic", "structural"):
                errors.append(f"{item_path}.proposed_kind 限 semantic|structural")

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
