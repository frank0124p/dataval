"""設計模式（design mode）：input 只有 context.md、還沒有 DDL 的 subject。

模式判定（一 subject 一資料夾，run.py 自動判定並在 console 標示）：
    input/<名>/<名>.sql 存在        → 🛡 govern mode（治理：閘門檢核＋顧問迭代）
    只有 input/<名>/context.md      → 🎨 design mode（設計：產設計文件與草稿 DDL）

design mode 沿用治理流程同一套「零 LLM ＋ agent 補語意」架構：
  1. run.py（零 LLM）依 context.md ＋ 參考模型（erd／表用途／naming／
     flows E2E 流程／ssot 權威登錄）＋閘門規則清單，
     組出 reports/<名>.design_prompt.md
  2. agent 用自身 LLM 依 prompt 產出 reports/<名>.design_result.json
     （格式見 config/_engine/design_result.schema.json）
  3. 重跑 run.py（可只點名該 subject）→ 確定性渲染三份設計產物：
       reports/<名>.logical_design.md    邏輯設計文件
       reports/<名>.physical_design.md   實體設計文件（含草稿 DDL 的閘門預檢）
       reports/<名>.design.sql           草稿 DDL 設計檔（每輪演進）
     設計輪次快照與演進 diff 記錄在 iterations/<名>/design/。
  4. 使用者把 design.sql 定稿為 input/<名>/<名>.sql（＋relations.yaml）後，
     subject 自動切換為 govern mode——設計輪次與治理迭代（answers.yaml 的
     iteration）是兩條獨立的演進軸。

此模組完全確定性、不接 LLM：prompt 組裝、result 驗證、文件渲染、輪次追蹤
都是純函式；語意內容一律由 agent 產生。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re

from .precheck import parse_context

FORMAT = "dataval.design_round.v1"
_ROUND_FILE = re.compile(r"^round_(\d+)\.json$")
#: 輪際 DDL diff 最多呈現行數（全文都在輪次快照內，不截斷）
DIFF_MAX_LINES = 120


# ---------------------------------------------------------------- 模式判定

def find_design_subjects(input_dir: str) -> list[tuple[str, str]]:
    """回傳 design mode 的 subject：[(名稱, 資料夾)]。

    判定：input/<名>/ 有 context.md、但沒有 <名>.sql／<名>.ddl。
    有 DDL 的資料夾是 govern mode（由 find_ddls 撿走）；兩者互斥。"""
    if not os.path.isdir(input_dir):
        return []
    out: list[tuple[str, str]] = []
    for entry in sorted(os.listdir(input_dir)):
        folder = os.path.join(input_dir, entry)
        if not os.path.isdir(folder) or entry.endswith(".samples"):
            continue
        has_ddl = any(os.path.isfile(os.path.join(folder, entry + ext))
                      for ext in (".sql", ".ddl"))
        if not has_ddl and os.path.isfile(os.path.join(folder, "context.md")):
            out.append((entry, folder))
    return out


# ---------------------------------------------------------------- prompt 組裝

def _read(path: str, limit: int = 6000) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return ""
    if len(text) > limit:
        return text[:limit] + "\n…（過長截斷）"
    return text


def _domain_folders(config_dir: str, domains: list[str]) -> list[str]:
    folders = {f.lower(): f for f in os.listdir(config_dir)
               if os.path.isdir(os.path.join(config_dir, f))
               and not f.startswith("_")}
    out: list[str] = []
    for want in ["Common"] + [d for d in (domains or []) if d]:
        folder = folders.get(want.strip().lower())
        if folder and folder not in out:
            out.append(folder)
    return out


def _reference_sections(config_dir: str, domains: list[str]) -> list[str]:
    """參考模型素材（宣告 domain＋Common）：erd 全文＋參考表用途＋naming 詞彙
    ＋flows E2E 流程＋ssot 權威登錄——設計時據以對齊既有資產與權威邊界。"""
    lines: list[str] = []
    for folder in _domain_folders(config_dir, domains):
        erd_dir = os.path.join(config_dir, folder, "erd")
        if os.path.isdir(erd_dir):
            for fn in sorted(os.listdir(erd_dir)):
                if not fn.endswith((".md", ".mmd", ".mermaid")) or \
                        fn.lower().startswith("readme"):
                    continue
                lines += [f"### 參考 ER 模型 `{folder}/erd/{fn}`", "",
                          _read(os.path.join(erd_dir, fn)), ""]
        tables_dir = os.path.join(erd_dir, "tables")
        if os.path.isdir(tables_dir):
            for fn in sorted(os.listdir(tables_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme"):
                    lines += [f"### 參考表用途 `{folder}/erd/tables/{fn}`", "",
                              _read(os.path.join(tables_dir, fn), 2000), ""]
        naming_dir = os.path.join(config_dir, folder, "naming")
        if os.path.isdir(naming_dir):
            for fn in sorted(os.listdir(naming_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme"):
                    lines += [f"### 詞彙字典 `{folder}/naming/{fn}`", "",
                              _read(os.path.join(naming_dir, fn), 4000), ""]
        flows_dir = os.path.join(config_dir, folder, "flows")
        if os.path.isdir(flows_dir):
            for fn in sorted(os.listdir(flows_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme") \
                        and not fn.startswith("_"):
                    lines += [f"### E2E 業務流程 `{folder}/flows/{fn}`", "",
                              _read(os.path.join(flows_dir, fn), 4000), ""]
        ssot_dir = os.path.join(config_dir, folder, "ssot")
        if os.path.isdir(ssot_dir):
            for fn in sorted(os.listdir(ssot_dir)):
                if fn.endswith((".yaml", ".yml", ".md")) and \
                        not fn.lower().startswith("readme"):
                    lines += [f"### SSOT 權威登錄 `{folder}/ssot/{fn}`",
                              "（設計的表不得與既有權威重複承載同一事實；"
                              "引用權威實體時只存鍵）", "",
                              "```yaml" if fn.endswith((".yaml", ".yml"))
                              else "",
                              _read(os.path.join(ssot_dir, fn), 4000),
                              "```" if fn.endswith((".yaml", ".yml")) else "",
                              ""]
    return [x for x in lines if x is not None] or \
        ["（宣告的 domain 沒有可用的參考模型素材）"]


def _gating_constraints(compiled_path: str, domains: list[str]) -> list[str]:
    """閘門規則清單（設計約束）：設計稿 DDL 之後要過這些規則。"""
    try:
        with open(compiled_path, encoding="utf-8") as f:
            compiled = json.load(f)
    except Exception:
        return ["（讀不到 compiled rules，略過）"]
    wanted = {"common"} | {d.strip().lower() for d in (domains or []) if d}
    out = []
    for rule in compiled.get("rules", []):
        if rule.get("zone") != "gating":
            continue
        if rule.get("domain", "Common").lower() not in wanted:
            continue
        out.append(f"- `{rule['id']}`（{rule.get('enforcement', 'warning')}）："
                   f"{rule.get('title', rule['id'])}")
    return out or ["（無適用的閘門規則）"]


def build_design_prompt(name: str, context_text: str, config_dir: str,
                        compiled_path: str) -> str:
    """組出 design mode 的補完任務 prompt（純函式、零 LLM）。"""
    meta, _ = parse_context(context_text)
    domains = [str(d) for d in (meta.get("domains") or [])]
    lines = [
        f"# 設計模式補完任務（design mode — {name}，給 agent）", "",
        "這個 subject 只有 `context.md`、還沒有 DDL——請你（agent）用自身 LLM，",
        "從語意描述與參考模型起草**邏輯設計、實體設計與草稿 DDL**。",
        "設計是草稿（design mode 產物），不是權威輸入；定稿與否由使用者決定。", "",
        "## 你要做的事", "",
        f"1. 細讀下方 context.md 與參考模型素材，起草 `{name}` 的：",
        "   - **logical_design**：業務實體、屬性、粒度（一行代表什麼）、",
        "     實體間關係與基數——用業務語言，不含實作細節。",
        "   - **physical_design**：ClickHouse 資料表規格（表名、欄位、型別、",
        "     Nullable、COMMENT、ENGINE、ORDER BY、PARTITION BY）與設計取捨說明。",
        "   - **draft_ddl**：可執行的 ClickHouse CREATE TABLE 草稿（含每欄 COMMENT），",
        "     必須盡量符合下方「設計約束」列出的閘門規則——設計稿之後會用",
        "     同一套規則預檢。",
        "   - **open_questions**：設計時拿不準、需要使用者決策的問題（繁中提問語氣）。",
        f"2. 寫成 JSON：`reports/{name}.design_result.json`，格式見",
        "   `config/_engine/design_result.schema.json`，骨架：",
        "```json",
        json.dumps({
            "logical_design": {
                "overview": "這個 subject 的設計總覽（繁中）",
                "entities": [{"name": "實體名", "description": "…",
                              "grain": "一行代表什麼",
                              "attributes": [{"name": "屬性", "description": "…",
                                              "business_key": True}]}],
                "relationships": [{"from": "實體A", "to": "實體B",
                                   "cardinality": "N:1", "description": "…"}],
            },
            "physical_design": {
                "overview": "實作策略總覽（繁中）",
                "tables": [{"name": "表名", "engine": "MergeTree()",
                            "order_by": "(id)", "partition_by": "",
                            "comment": "表用途",
                            "columns": [{"name": "欄", "type": "UInt64",
                                         "nullable": False, "comment": "…"}]}],
                "notes": ["設計取捨與注意事項"],
            },
            "draft_ddl": "CREATE TABLE …;",
            "open_questions": ["給使用者的設計提問"],
        }, ensure_ascii=False, indent=2),
        "```",
        f"3. 重跑 `python run.py {name}` → 工具會確定性渲染",
        f"   `reports/{name}.logical_design.md`、`{name}.physical_design.md`、",
        f"   `{name}.design.sql`，並對 draft_ddl 做閘門預檢、記錄設計輪次。",
        "4. 向使用者回報：第幾輪設計、預檢結果、open_questions，並提醒——",
        f"   設計定稿後由**使用者**把 design.sql 存成 `input/{name}/{name}.sql`",
        "   （＋補 relations.yaml）進入 govern mode；agent 不得代寫權威輸入。", "",
        "## context.md（唯一的語意輸入）", "",
        "```markdown", context_text.strip(), "```", "",
        f"（front-matter 解析：subject=`{meta.get('subject', '')}`、"
        f"domains={domains or '[]'}、business_keys="
        f"{meta.get('business_keys') or '{}'}）", "",
        "## 設計約束（閘門規則——draft_ddl 之後要過這些）", "",
    ]
    lines += _gating_constraints(compiled_path, domains)
    lines += ["", "## 參考模型素材（宣告 domain ＋ Common）", ""]
    lines += _reference_sections(config_dir, domains)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- result 驗證

def validate_design_result(result) -> list[str]:
    """驗證 design_result 的結構（無外部依賴；語意由渲染與預檢把關）。"""
    errors: list[str] = []
    if not isinstance(result, dict):
        return ["最外層必須是 JSON object"]
    required = {"logical_design", "physical_design", "draft_ddl"}
    optional = {"open_questions"}
    missing = required - set(result)
    extra = set(result) - required - optional
    if missing:
        errors.append(f"缺少必要欄位：{sorted(missing)}")
    if extra:
        errors.append(f"不允許的欄位：{sorted(extra)}")

    logical = result.get("logical_design")
    if not isinstance(logical, dict):
        errors.append("logical_design 必須是 object")
    else:
        if not str(logical.get("overview", "")).strip():
            errors.append("logical_design.overview 必須是非空字串")
        entities = logical.get("entities")
        if not isinstance(entities, list) or not entities:
            errors.append("logical_design.entities 必須是非空 array")
        else:
            for i, ent in enumerate(entities):
                if not isinstance(ent, dict) or not str(ent.get("name", "")).strip():
                    errors.append(f"logical_design.entities[{i}] 必須含非空 name")
        if not isinstance(logical.get("relationships", []), list):
            errors.append("logical_design.relationships 必須是 array")

    physical = result.get("physical_design")
    if not isinstance(physical, dict):
        errors.append("physical_design 必須是 object")
    else:
        tables = physical.get("tables")
        if not isinstance(tables, list) or not tables:
            errors.append("physical_design.tables 必須是非空 array")
        else:
            for i, table in enumerate(tables):
                if not isinstance(table, dict) or not str(table.get("name", "")).strip():
                    errors.append(f"physical_design.tables[{i}] 必須含非空 name")
                elif not isinstance(table.get("columns", []), list):
                    errors.append(f"physical_design.tables[{i}].columns 必須是 array")

    if not str(result.get("draft_ddl", "")).strip():
        errors.append("draft_ddl 必須是非空字串（ClickHouse CREATE TABLE 草稿）")
    oq = result.get("open_questions")
    if oq is not None and (not isinstance(oq, list) or
                           any(not isinstance(x, str) for x in oq)):
        errors.append("open_questions 必須是字串 array")
    return errors


# ---------------------------------------------------------------- 輪次追蹤

def _design_dir(history_root: str, subject: str) -> str:
    return os.path.join(history_root, subject, "design")


def _recorded_rounds(dirp: str) -> list[int]:
    if not os.path.isdir(dirp):
        return []
    return sorted(int(m.group(1)) for fn in os.listdir(dirp)
                  if (m := _ROUND_FILE.match(fn)))


def _load_round(dirp: str, round_no: int) -> dict | None:
    path = os.path.join(dirp, f"round_{round_no}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if data.get("format") == FORMAT else None
    except Exception:
        return None


def _write_if_changed(path: str, text: str) -> None:
    old = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def track_round(history_root: str, subject: str, context_text: str,
                result: dict) -> dict:
    """設計輪次：內容（context＋design_result）不變＝同輪重渲染；
    變了＝輪次 +1 並存快照。回傳 {round, first, changed, ddl_diff}。"""
    dirp = _design_dir(history_root, subject)
    digest = {
        "context_sha": hashlib.sha256(context_text.encode("utf-8")).hexdigest(),
        "result_sha": hashlib.sha256(json.dumps(
            result, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
    }
    rounds = _recorded_rounds(dirp)
    latest = _load_round(dirp, rounds[-1]) if rounds else None
    if latest and latest.get("context_sha") == digest["context_sha"] \
            and latest.get("result_sha") == digest["result_sha"]:
        return {"round": rounds[-1], "first": False, "changed": False,
                "ddl_diff": latest.get("ddl_diff") or ""}

    round_no = (rounds[-1] + 1) if rounds else 1
    ddl_diff = ""
    if latest:
        diff_lines = list(difflib.unified_diff(
            str(latest.get("draft_ddl", "")).splitlines(),
            str(result.get("draft_ddl", "")).splitlines(),
            fromfile=f"第{rounds[-1]}輪設計", tofile=f"第{round_no}輪設計",
            lineterm=""))
        if len(diff_lines) > DIFF_MAX_LINES:
            diff_lines = diff_lines[:DIFF_MAX_LINES] + ["…（diff 過長截斷）"]
        ddl_diff = "\n".join(diff_lines)
    payload = {"format": FORMAT, "subject": subject, "round": round_no,
               **digest, "draft_ddl": str(result.get("draft_ddl", "")),
               "result": result, "ddl_diff": ddl_diff}
    os.makedirs(dirp, exist_ok=True)
    with open(os.path.join(dirp, f"round_{round_no}.json"), "w",
              encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)
    _rebuild_history(dirp, subject)
    return {"round": round_no, "first": round_no == 1,
            "changed": round_no > 1, "ddl_diff": ddl_diff}


def _rebuild_history(dirp: str, subject: str) -> None:
    lines = [f"# 設計歷史（design mode）— {subject}", "",
             "每輪由 run.py 自動記錄；快照見同資料夾 `round_<N>.json`。", ""]
    for n in _recorded_rounds(dirp):
        data = _load_round(dirp, n) or {}
        result = data.get("result") or {}
        tables = (result.get("physical_design") or {}).get("tables") or []
        oq = result.get("open_questions") or []
        lines.append(f"## 第 {n} 輪設計")
        lines.append(f"- 資料表 {len(tables)} 張："
                     + ("、".join(f"`{t.get('name', '?')}`" for t in tables)
                        or "（無）"))
        lines.append(f"- 待使用者決策的設計提問：{len(oq)}")
        lines.append("- 相對前一輪：" + ("首稿" if n == 1 else
                     ("DDL 已演進（diff 見 round 快照）"
                      if data.get("ddl_diff") else "DDL 不變")))
        lines.append("")
    _write_if_changed(os.path.join(dirp, "HISTORY.md"), "\n".join(lines))


# ---------------------------------------------------------------- 文件渲染

def _logical_md(name: str, round_no: int, result: dict) -> str:
    logical = result.get("logical_design") or {}
    lines = [f"# 邏輯設計（Logical Design）— {name}（第 {round_no} 輪設計）", "",
             "> 🎨 design mode 產物：由 `context.md` 與參考模型起草（agent LLM），",
             "> 設計歷史見 `iterations/<名>/design/HISTORY.md`。定稿與否由使用者決定。",
             "", "## 設計總覽", "", str(logical.get("overview", "")).strip(), "",
             "## 業務實體"]
    for ent in logical.get("entities") or []:
        lines += ["", f"### {ent.get('name', '?')}",
                  str(ent.get("description", "")).strip()]
        if ent.get("grain"):
            lines.append(f"- **粒度**：{ent['grain']}")
        attrs = ent.get("attributes") or []
        if attrs:
            lines += ["", "| 屬性 | 說明 | Business Key |", "|---|---|---|"]
            lines += [f"| `{a.get('name', '')}` | {a.get('description', '')} "
                      f"| {'✅' if a.get('business_key') else ''} |"
                      for a in attrs]
    rels = logical.get("relationships") or []
    lines += ["", "## 實體關係", ""]
    if rels:
        lines += ["| from | to | 基數 | 說明 |", "|---|---|---|---|"]
        lines += [f"| `{r.get('from', '')}` | `{r.get('to', '')}` "
                  f"| {r.get('cardinality', '')} | {r.get('description', '')} |"
                  for r in rels]
    else:
        lines.append("（無）")
    oq = result.get("open_questions") or []
    lines += ["", "## 待使用者決策的設計提問", ""]
    lines += [f"- {q}" for q in oq] or ["（無）"]
    return "\n".join(lines) + "\n"


def _physical_md(name: str, round_no: int, result: dict,
                 gate_preview: dict | None, ddl_diff: str) -> str:
    physical = result.get("physical_design") or {}
    lines = [f"# 實體設計（Physical Design）— {name}（第 {round_no} 輪設計）", "",
             "> 🎨 design mode 產物：草稿 DDL 見同名 `"
             f"reports/{name}.design.sql`；定稿後由使用者存成 "
             f"`input/{name}/{name}.sql` 進入 govern mode。",
             "", "## 實作策略", "", str(physical.get("overview", "")).strip(), "",
             "## 資料表規格"]
    for table in physical.get("tables") or []:
        lines += ["", f"### `{table.get('name', '?')}`",
                  str(table.get("comment", "")).strip(), "",
                  f"- ENGINE：`{table.get('engine', '')}`"
                  + (f" · ORDER BY `{table.get('order_by', '')}`"
                     if table.get("order_by") else "")
                  + (f" · PARTITION BY `{table.get('partition_by', '')}`"
                     if table.get("partition_by") else "")]
        cols = table.get("columns") or []
        if cols:
            lines += ["", "| 欄位 | 型別 | Nullable | COMMENT |", "|---|---|---|---|"]
            lines += [f"| `{c.get('name', '')}` | `{c.get('type', '')}` "
                      f"| {'✅' if c.get('nullable') else ''} "
                      f"| {c.get('comment', '')} |" for c in cols]
    lines += ["", "## 閘門預檢（以目前規則試跑草稿 DDL；設計參考、非正式判定）", ""]
    if not gate_preview:
        lines.append("（本輪未執行預檢）")
    elif gate_preview.get("parse_error"):
        lines.append(f"❌ 草稿 DDL 無法解析：{gate_preview['parse_error']}")
    else:
        flag = "✅ 預檢合規" if gate_preview.get("compliant") else "❌ 預檢不合規"
        lines.append(f"{flag} ｜ fail {gate_preview.get('fail', 0)}、"
                     f"warning {gate_preview.get('warning', 0)}")
        if gate_preview.get("blocked"):
            lines.append("卡下來的規則：" + "、".join(
                f"`{r}`" for r in gate_preview["blocked"]))
    notes = physical.get("notes") or []
    lines += ["", "## 設計注意事項", ""]
    lines += [f"- {n}" for n in notes] or ["（無）"]
    if ddl_diff:
        lines += ["", "## 與上一輪設計的 DDL 演進", "", "```diff", ddl_diff, "```"]
    return "\n".join(lines) + "\n"


def design_sql_text(name: str, round_no: int, result: dict) -> str:
    return (f"-- 第 {round_no} 輪設計 DDL — {name}（design mode 草稿，會隨迭代演進）\n"
            f"-- 邏輯／實體設計見 reports/{name}.logical_design.md、"
            f"{name}.physical_design.md\n"
            f"-- 定稿後由使用者存成 input/{name}/{name}.sql（＋relations.yaml）"
            "進入 govern mode\n\n"
            + str(result.get("draft_ddl", "")).strip() + "\n")


def render(name: str, result: dict, context_text: str, history_root: str,
           report_dir: str, gate_preview: dict | None = None) -> dict:
    """輪次追蹤＋渲染三份設計產物。回傳 track_round 的資訊＋檔案路徑。"""
    info = track_round(history_root, name, context_text, result)
    round_no = info["round"]
    outputs = {
        f"{name}.logical_design.md": _logical_md(name, round_no, result),
        f"{name}.physical_design.md": _physical_md(
            name, round_no, result, gate_preview, info.get("ddl_diff", "")),
        f"{name}.design.sql": design_sql_text(name, round_no, result),
    }
    os.makedirs(report_dir, exist_ok=True)
    for fname, text in outputs.items():
        _write_if_changed(os.path.join(report_dir, fname), text)
    info["files"] = sorted(outputs)
    return info
