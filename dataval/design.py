"""設計模式（design mode）：input 只有 context.md、還沒有 DDL 的 subject。

模式判定（一 subject 一資料夾，run.py 自動判定並在 console 標示）：
    input/<名>/<名>.sql 存在        → 🛡 govern mode（治理：閘門檢核＋顧問迭代）
    只有 input/<名>/context.md      → 🎨 design mode（設計：產設計文件與草稿 DDL）

design mode 沿用治理流程同一套「零 LLM ＋ agent 補語意」架構：
  1. run.py（零 LLM）依 context.md ＋ 參考模型（erd／表用途／naming／
     flows E2E 流程／ssot 權威登錄）＋閘門規則清單，
     組出 design_doc/<名>/<名>.design_prompt.md
  2. agent 用自身 LLM 依 prompt 產出 design_doc/<名>/<名>.design_result.json
     （格式見 config/_engine/design_result.schema.json）
  3. 重跑 run.py（可只點名該 subject）→ 確定性渲染三份設計產物：
       design_doc/<名>/<名>.logical_design.md    邏輯設計文件
       design_doc/<名>/<名>.physical_design.md   實體設計文件（含草稿 DDL 的閘門預檢）
       design_doc/<名>/<名>.design.sql           草稿 DDL 設計檔（每輪演進）
     設計輪次快照與演進 diff 記錄在 iterations/<名>/design/。
  4. 使用者把 design.sql 定稿為 input/<名>/<名>.sql（＋relations.yaml）後，
     subject 自動切換為 govern mode——設計輪次與治理迭代（answers.yaml 的
     iteration）是兩條獨立的演進軸。

設計問答迴圈（design_answers.yaml）：
  - agent 起草時每題 open_question 附 proposed_answer 代填答案；
    run.py 渲染後把「尚未覆蓋」的提問寫進 input/<名>/design_answers.yaml
    標 status: proposed（待驗證），永不覆寫既有條目。
  - 使用者驗證＝把 proposed 改 answered（答案可修改）或 deferred（不追）。
    agent 不得自行把 proposed 改成 answered。
  - 下一輪 prompt 自動帶入已答條目（已澄清、勿重問、依答案修設計）與
    擱置條目（勿重問）→ agent 重新起草 → 內容變了輪次自動 +1。

此模組完全確定性、不接 LLM：prompt 組裝、result 驗證、文件渲染、輪次追蹤
都是純函式；語意內容一律由 agent 產生。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re

import yaml

from . import docpaths, etl_manifest
from .parser import parse_ddl
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


# ---------------------------------------------------------------- 設計問答

def question_text(q) -> str:
    """open_questions 條目 → 提問文字（相容純字串與 object 兩種形）。"""
    return str(q.get("question", "")) if isinstance(q, dict) else str(q)


def question_id(text: str) -> str:
    """提問文字 → 穩定 id（跨輪不變；改寫措辭視為新題）。"""
    return "dq-" + hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:8]


def answers_file(input_folder: str) -> str:
    return os.path.join(input_folder, "design_answers.yaml")


def load_design_answers(path: str) -> tuple[dict, list[str]]:
    """讀設計問答檔。壞檔不改寫，只回報 problems（此時不代填新條目）。"""
    empty = {"version": 1, "answers": []}
    if not os.path.isfile(path):
        return empty, []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        return empty, [f"design_answers.yaml 解析失敗：{type(e).__name__}: {e}"]
    if not isinstance(data, dict) or not isinstance(data.get("answers"), list):
        return empty, ["design_answers.yaml 格式不正確（根節點需含 answers list）"]
    return {"version": 1, "answers": data["answers"]}, []


def qa_state(data: dict) -> dict:
    """答題狀態分組：answered／proposed／deferred（其他狀態視同 proposed）。"""
    out: dict = {"answered": [], "proposed": [], "deferred": []}
    for entry in data.get("answers") or []:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "proposed"))
        out.setdefault(status if status in out else "proposed", []).append(entry)
    return out


def merge_design_answers(data: dict, open_questions: list) -> tuple[dict, int]:
    """把本輪設計提問併入問答檔：只新增未覆蓋的題、永不覆寫既有條目。"""
    covered = {str(e.get("id") or question_id(question_text(e)))
               for e in data.get("answers") or [] if isinstance(e, dict)}
    added = 0
    for q in open_questions or []:
        text = question_text(q).strip()
        if not text:
            continue
        qid = question_id(text)
        if qid in covered:
            continue
        data["answers"].append({
            "id": qid,
            "question": text,
            "answer": (str(q.get("proposed_answer", "")).strip()
                       if isinstance(q, dict) else ""),
            "status": "proposed",
        })
        covered.add(qid)
        added += 1
    return data, added


def answers_to_yaml(data: dict, subject: str) -> str:
    header = (
        "# 設計問答（design mode）。agent 代填的條目標 proposed，等你驗證：\n"
        "#   答案沒問題 → status 改 answered（answer 可修改）；\n"
        "#   不想追了 → 改 deferred。agent 不得自行把 proposed 改 answered。\n"
        "# answered 條目下一輪自動帶入設計 prompt（已澄清、勿重問、依答案修設計）；\n"
        f"# 重要決定也建議回寫 input/{subject}/context.md（語意的權威來源）。\n")
    return header + yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


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


def reference_materials(config_dir: str,
                        domains: list[str]) -> list[tuple[str, str]]:
    """設計素材清單（宣告 domain＋Common）：[(素材類型, config 相對路徑)]。
    prompt 組裝與設計出處（provenance）共用同一次掃描，確保兩邊一致。"""
    out: list[tuple[str, str]] = []
    for folder in _domain_folders(config_dir, domains):
        erd_dir = os.path.join(config_dir, folder, "erd")
        if os.path.isdir(erd_dir):
            for fn in sorted(os.listdir(erd_dir)):
                if fn.endswith((".md", ".mmd", ".mermaid")) and \
                        not fn.lower().startswith("readme"):
                    out.append(("參考 ER 模型", f"config/{folder}/erd/{fn}"))
        tables_dir = os.path.join(erd_dir, "tables")
        if os.path.isdir(tables_dir):
            for fn in sorted(os.listdir(tables_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme"):
                    out.append(("參考表用途",
                                f"config/{folder}/erd/tables/{fn}"))
        naming_dir = os.path.join(config_dir, folder, "naming")
        if os.path.isdir(naming_dir):
            for fn in sorted(os.listdir(naming_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme"):
                    out.append(("詞彙字典", f"config/{folder}/naming/{fn}"))
        flows_dir = os.path.join(config_dir, folder, "flows")
        if os.path.isdir(flows_dir):
            for fn in sorted(os.listdir(flows_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme") \
                        and not fn.startswith("_"):
                    out.append(("E2E 業務流程", f"config/{folder}/flows/{fn}"))
        ssot_dir = os.path.join(config_dir, folder, "ssot")
        if os.path.isdir(ssot_dir):
            for fn in sorted(os.listdir(ssot_dir)):
                if fn.endswith((".yaml", ".yml", ".md")) and \
                        not fn.lower().startswith("readme"):
                    out.append(("SSOT 權威登錄", f"config/{folder}/ssot/{fn}"))
        knowhow_dir = os.path.join(config_dir, folder, "knowhow")
        if os.path.isdir(knowhow_dir):
            out.append(("設計約束（閘門規則）", f"config/{folder}/knowhow/"))
        advisory_dir = os.path.join(knowhow_dir, "advisory")
        if os.path.isdir(advisory_dir):
            for fn in sorted(os.listdir(advisory_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme"):
                    out.append(("設計 know-how（顧問規則）",
                                f"config/{folder}/knowhow/advisory/{fn}"))
        prod_dir = os.path.join(config_dir, folder, "production")
        if os.path.isdir(prod_dir):
            for fn in sorted(os.listdir(prod_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme"):
                    out.append(("正式區資產",
                                f"config/{folder}/production/{fn}"))
        products_dir = os.path.join(config_dir, folder, "products")
        if os.path.isdir(products_dir):
            for fn in sorted(os.listdir(products_dir)):
                if fn.endswith(".md") and not fn.lower().startswith("readme"):
                    out.append(("產品縮寫註冊表",
                                f"config/{folder}/products/{fn}"))
    return out


def _merged_glossary_lines(config_dir: str, domains: list[str]) -> list[str]:
    """詞彙字典：改用**解析後的合併形式**（Common＋宣告域，domain 覆蓋）——
    比逐檔塞全文小得多、且合併語意正確（agent 不必自己腦內合併多份）。"""
    from .engine import load_glossary
    g = load_glossary(config_dir, domains)
    lines = ["### 詞彙字典（Common＋宣告域合併後；維護見 config/<域>/naming/）",
             ""]
    banned = g.get("banned_terms") or {}
    aliases = g.get("aliases") or {}
    standard = g.get("standard_terms") or []
    lines.append("- **禁用詞 → 改用**：" + ("、".join(
        f"`{k}`→`{v}`" for k, v in sorted(banned.items())) or "（無）"))
    lines.append("- **別名 → 正規詞**：" + ("、".join(
        f"`{k}`→`{v}`" for k, v in sorted(aliases.items())) or "（無）"))
    lines.append("- **標準詞白名單**：" + ("、".join(
        f"`{x}`" for x in sorted(standard))
        if standard else "（未啟用——黑名單模式）"))
    lines.append("")
    return lines


#: 這些素材類型不 inline 全文：規則已有「設計約束」「設計 know-how」
#: 緊湊章節，重複塞全文只會灌爆 agent context。
_PROMPT_SKIP_KINDS = {"設計約束（閘門規則）", "設計 know-how（顧問規則）"}

#: 素材類型 → 預設適用階段（L=logical 起草、P=physical/DDL 落地）。
#: 檔案 front-matter 的 index_stage 可覆蓋。
_DEFAULT_STAGE = {"參考 ER 模型": ["L"], "參考表用途": ["L"],
                  "E2E 業務流程": ["L"], "SSOT 權威登錄": ["L", "P"],
                  "詞彙字典": ["P"], "產品縮寫註冊表": ["P"],
                  "正式區資產": ["L", "P"]}
#: 預設必讀（漏讀最容易出事的素材）；front-matter index_required 可覆蓋。
#: 正式區資產＝已核准上線的主體，設計新表前一定要先看過有沒有能複用的。
_DEFAULT_REQUIRED = {"SSOT 權威登錄", "正式區資產"}


def _index_meta(fs_path: str) -> dict:
    """讀素材檔 front-matter 的三個索引欄位（都選填、容錯）：
    index_summary（一句話摘要）、index_stage（L/P）、index_required。"""
    if not fs_path.endswith(".md"):
        return {}
    try:
        with open(fs_path, encoding="utf-8") as f:
            meta, _ = parse_context(f.read())
    except Exception:
        return {}
    out: dict = {}
    if str(meta.get("index_summary", "")).strip():
        out["summary"] = str(meta["index_summary"]).strip()
    raw_stage = meta.get("index_stage")
    if raw_stage:
        items = raw_stage if isinstance(raw_stage, list) else [raw_stage]
        stages = [s for s in (str(x).strip().upper() for x in items)
                  if s in ("L", "P")]
        if stages:
            out["stage"] = stages
    if isinstance(meta.get("index_required"), bool):
        out["required"] = meta["index_required"]
    return out


def _auto_summary(kind: str, fs_path: str) -> str:
    """確定性自動摘要（front-matter 未提供 index_summary 時的底）。"""
    try:
        with open(fs_path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return os.path.basename(fs_path)
    try:
        if kind == "參考 ER 模型":
            from .er_diagram import extract_mermaid, parse_mermaid
            parsed = parse_mermaid(extract_mermaid(text)
                                   if fs_path.endswith(".md") else text)
            ents = sorted(parsed.get("entities") or {})
            return ("實體：" + "、".join(ents[:6])
                    + ("…" if len(ents) > 6 else "")) if ents else "（無實體）"
        if kind == "詞彙字典":
            from .engine import _glossary_from_md
            g = _glossary_from_md(text)
            std = g.get("standard_terms") or []
            return (f"禁用 {len(g.get('banned_terms') or {})}、"
                    f"別名 {len(g.get('aliases') or {})}、"
                    + (f"標準詞 {len(std)}" if std else "白名單未啟用"))
        if kind == "SSOT 權威登錄":
            data = yaml.safe_load(text) or {}
            ents = sorted((data.get("registry") or {}))
            return ("權威登錄：" + "、".join(ents[:5])
                    + ("…" if len(ents) > 5 else "")) if ents else "（空登錄）"
        if kind == "產品縮寫註冊表":
            codes = re.findall(r"^\s*\|\s*`?(\w{2,4})`?\s*\|", text, re.M)
            skip = {"縮寫", "前綴", "ods", "dim", "dwd", "dws", "ads"}
            names = [c for c in codes if c.lower() not in skip
                     and set(c) - {"-", ":"}]
            return ("產品：" + "、".join(dict.fromkeys(names))
                    if names else "（尚無產品，含分層前綴定義）")
    except Exception:
        pass
    # 通用 fallback：第一個非空、非標題、非 front-matter 行
    body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "|", "```", "-")):
            return line[:60] + ("…" if len(line) > 60 else "")
    return os.path.basename(fs_path)


def design_index(config_dir: str, domains: list[str]) -> list[dict]:
    """素材索引：每份素材一列——路徑、摘要（front-matter 覆蓋自動萃取）、
    適用階段、必讀標記。agent 據此**按需開檔**，不必一次讀全部。"""
    out = []
    for kind, path in reference_materials(config_dir, domains):
        if kind in _PROMPT_SKIP_KINDS:
            continue    # 規則類內嵌於 prompt 緊湊章節，不入索引
        fs_path = os.path.join(config_dir, path[len("config/"):])
        curated = _index_meta(fs_path)
        out.append({
            "kind": kind, "path": path,
            "summary": curated.get("summary") or _auto_summary(kind, fs_path),
            "auto_summary": "summary" not in curated,
            "stage": curated.get("stage") or _DEFAULT_STAGE.get(kind, ["L"]),
            "required": curated.get("required",
                                    kind in _DEFAULT_REQUIRED),
        })
    return out


def _reference_index_lines(config_dir: str, domains: list[str]) -> list[str]:
    """索引模式素材區：目錄＋按階段閱讀指引；合併字典內嵌（每案必用）。"""
    entries = design_index(config_dir, domains)
    lines = ["**按需開檔，勿一次全讀**：起草 logical（六節）前先讀標 `L` 的"
             "素材；做 physical／DDL 前再讀標 `P` 的。標 **必讀** 的素材"
             "一定要讀並列入 narrative.references。", ""]
    if entries:
        lines += ["| 素材 | 路徑（用 Read 開啟） | 摘要 | 階段 | 必讀 |",
                  "|---|---|---|---|---|"]
        for e in entries:
            lines.append(
                f"| {e['kind']} | `{e['path']}` "
                f"| {e['summary']}{'（🤖 自動摘要）' if e['auto_summary'] else ''} "
                f"| {','.join(e['stage'])} "
                f"| {'✅ 必讀' if e['required'] else '—'} |")
        lines.append("")
    else:
        lines += ["（宣告的 domain 沒有可用的參考模型素材）", ""]
    lines += _merged_glossary_lines(config_dir, domains)   # 每案必用，內嵌
    return lines


def _reference_sections(config_dir: str, domains: list[str]) -> list[str]:
    """參考模型素材（宣告 domain＋Common）。效能與正確性原則：
    能解析的用**解析後緊湊形式**（詞彙字典合併、ER 圖只取 mermaid fence），
    不截斷破壞內容；規則類另有緊湊章節，不重複 inline 全文。"""
    limits = {"參考表用途": 2000, "E2E 業務流程": 4000,
              "SSOT 權威登錄": 4000, "產品縮寫註冊表": 2000}
    lines: list[str] = []
    glossary_done = False
    for kind, path in reference_materials(config_dir, domains):
        if kind in _PROMPT_SKIP_KINDS:
            continue
        if kind == "詞彙字典":
            if not glossary_done:          # 多檔合併後只呈現一次
                lines += _merged_glossary_lines(config_dir, domains)
                glossary_done = True
            continue
        rel = path[len("config/"):]
        fs_path = os.path.join(config_dir, rel)
        lines += [f"### {kind} `{rel}`"]
        if kind == "SSOT 權威登錄":
            lines.append("（設計的表不得與既有權威重複承載同一事實；"
                         "引用權威實體時只存鍵）")
        lines.append("")
        if kind == "參考 ER 模型" and path.endswith(".md"):
            # 只取 mermaid fence（模型本體），跳過說明散文
            from .er_diagram import extract_mermaid
            mermaid = extract_mermaid(_read(fs_path, 12000)).strip()
            if mermaid:
                lines += ["```mermaid", mermaid, "```", ""]
                continue
        is_yaml = path.endswith((".yaml", ".yml"))
        if is_yaml:
            lines.append("```yaml")
        lines.append(_read(fs_path, limits.get(kind, 6000)))
        if is_yaml:
            lines.append("```")
        lines.append("")
    return lines or ["（宣告的 domain 沒有可用的參考模型素材）"]


def _short(text: str, limit: int = 120) -> str:
    """規則描述取首段精華（單行、截斷），避免灌爆 prompt。"""
    line = " ".join(str(text or "").split())
    return line[:limit] + ("…" if len(line) > limit else "")


def _load_rules(compiled_path: str, domains: list[str],
                zone: str) -> list[dict] | None:
    try:
        with open(compiled_path, encoding="utf-8") as f:
            compiled = json.load(f)
    except Exception:
        return None
    wanted = {"common"} | {d.strip().lower() for d in (domains or []) if d}
    return [rule for rule in compiled.get("rules", [])
            if rule.get("zone") == zone
            and rule.get("domain", "Common").lower() in wanted]


_MD_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")


def load_products(config_dir: str, domains: list[str]) -> dict:
    """產品縮寫註冊表（config/<域>/products/*.md，Common＋宣告域合併，
    domain 覆蓋 Common）。段落標題關鍵字：產品/product → codes、
    分層/layer/前綴 → layers。回傳 {"codes": {縮寫: {name, desc, domain}},
    "layers": {前綴: 層級說明}}。"""
    out = {"codes": {}, "layers": {}}
    for folder in _domain_folders(config_dir, domains):
        pdir = os.path.join(config_dir, folder, "products")
        if not os.path.isdir(pdir):
            continue
        for fn in sorted(os.listdir(pdir)):
            if not fn.endswith(".md") or fn.lower().startswith("readme"):
                continue
            section = ""
            try:
                with open(os.path.join(pdir, fn), encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            for line in text.splitlines():
                if line.lstrip().startswith("#"):
                    head = line.lower()
                    if "產品" in line or "product" in head:
                        section = "codes"
                    elif "分層" in line or "layer" in head or "前綴" in line:
                        section = "layers"
                    else:
                        section = ""
                    continue
                m = _MD_ROW_RE.match(line)
                if not m or not section:
                    continue
                cells = [c.strip() for c in m.group(1).split("|")]
                if len(cells) < 2 or set(cells[0]) <= {"-", ":", " "} \
                        or cells[0] in ("縮寫", "前綴"):
                    continue
                key = cells[0].strip("`").lower()
                if not key:
                    continue
                if section == "codes":
                    out["codes"][key] = {"name": cells[1],
                                         "desc": cells[2] if len(cells) > 2
                                         else "", "domain": folder}
                else:
                    out["layers"][key] = cells[1]
    return out


def product_prefix_check(result: dict, product: dict | None) -> list[dict]:
    """表名產品前綴檢查（確定性）：context 宣告 product 時，設計內每張表
    必須符合 `<分層前綴>_<產品縮寫>_<語意名>`。回傳逐表結果。"""
    if not product or not str(product.get("code", "")).strip():
        return []
    code = str(product["code"]).lower()
    layers = [str(x).lower() for x in product.get("layers") or []] or \
        ["ods", "dim", "dwd", "dws", "ads"]
    pattern = re.compile(
        rf"^({'|'.join(re.escape(x) for x in layers)})_{re.escape(code)}_"
        r"[a-z0-9_]+$")
    rows = []
    for t in (result.get("physical_design") or {}).get("tables") or []:
        name = str(t.get("name", ""))
        rows.append({"table": name,
                     "ok": bool(pattern.match(name.lower())),
                     "expected": f"<{'|'.join(layers)}>_{code}_<語意名>"})
    return rows


def _gating_constraints(compiled_path: str, domains: list[str]) -> list[str]:
    """閘門規則清單（設計約束）：設計稿 DDL 之後要過這些規則。
    附各規則「目的」首段——設計時知其然也知其所以然。"""
    rules = _load_rules(compiled_path, domains, "gating")
    if rules is None:
        return ["（讀不到 compiled rules，略過）"]
    out = []
    for rule in rules:
        line = (f"- `{rule['id']}`（{rule.get('enforcement', 'warning')}）："
                f"{rule.get('title', rule['id'])}")
        purpose = _short(rule.get("purpose", ""))
        if purpose:
            line += f"\n  - 目的：{purpose}"
        out.append(line)
    return out or ["（無適用的閘門規則）"]


def _advisory_knowhow(compiled_path: str, domains: list[str]) -> list[str]:
    """顧問區 know-how（語意準則）：不擋、但描述「好設計長什麼樣」——
    起草時據以自我檢視，減少進治理後的顧問來回。"""
    rules = _load_rules(compiled_path, domains, "advisory")
    if rules is None:
        return ["（讀不到 compiled rules，略過）"]
    out = []
    for rule in rules:
        desc = _short(rule.get("check_llm") or rule.get("purpose") or "", 200)
        out.append(f"- `{rule['id']}`（{rule.get('domain', 'Common')}）："
                   f"{rule.get('title', rule['id'])}"
                   + (f"\n  - {desc}" if desc else ""))
    return out or ["（無適用的顧問準則）"]


def build_design_prompt(name: str, context_text: str, config_dir: str,
                        compiled_path: str,
                        answers: dict | None = None,
                        material_mode: str | None = None) -> str:
    """組出 design mode 的補完任務 prompt（純函式、零 LLM）。
    answers＝design_answers.yaml 的內容——已答條目帶入「已澄清」、
    擱置條目帶入「勿重問」；proposed 不餵（未驗證的代填不迴聲放大）。"""
    meta, _ = parse_context(context_text)
    domains = [str(d) for d in (meta.get("domains") or [])]
    lines = [
        f"# 設計模式補完任務（design mode — {name}，給 agent）", "",
        "這個 subject 只有 `context.md`、還沒有 DDL——請你（agent）用自身 LLM，",
        "從語意描述與參考模型起草**邏輯設計、實體設計與草稿 DDL**。",
        "設計是草稿（design mode 產物），不是權威輸入；定稿與否由使用者決定。", "",
        "## 你要做的事", "",
        f"1. 細讀下方 context.md 與參考模型素材，起草 `{name}` 的：",
        "   （**元件邊界**：logical＝業務世界長什麼樣，與技術無關；",
        "   physical＝在 ClickHouse 上怎麼落地，全是技術決定。檢驗法：",
        "   內容若換一個資料庫仍不變 → 放 logical；會變 → 放 physical。",
        "   實體與表不必 1:1——寬表／彙總層只存在於 physical。）",
        "   - **logical_design**（用業務語言，不含實作細節），五節缺一不可：",
        "     business_context（業務脈絡：為何存在、支撐哪些業務行為與消費者）、",
        "     domain_boundary（領域邊界：所屬 domain、本主體擁有哪些權威事實、",
        "     引用哪些外部權威——對照 SSOT 登錄，引用只存鍵）、",
        "     entities（實體總覽＋明細：類型 fact/dimension/event、粒度、",
        "     屬性、business key）、relationships（實體關係與基數）、",
        "     metric_contracts（指標契約：這個主體對下游承諾的指標——",
        "     名稱、定義口徑、粒度、來源欄位、注意事項）、",
        "     cross_domain_dependencies（跨域依賴：依賴哪個 domain 的哪個",
        "     實體、上游或下游、介接鍵——對照 SSOT 與參考模型，引用只存鍵）。",
        "   - **physical_design**：ClickHouse 資料表規格（表名、欄位、型別、",
        "     Nullable、COMMENT、ENGINE、ORDER BY、PARTITION BY）。",
        "     **積木化設計**：主體可拆成多張表分層組合——`layer` 標",
        "     base（小積木：源頭表）／intermediate（中積木：組合表）／",
        "     wide（寬表，可多張）；不必全部集中在一張寬表。",
        "     **每張表附自己的 `ddl`**（單獨可執行的 CREATE TABLE，會逐表",
        "     拆檔輸出 .ddl）。**每欄附 `source`（從何處來）**：",
        "     組合欄寫 `來源表.欄位`、外部權威寫 `DOMAIN.table.col`、",
        "     運算欄寫 `expression: …`、本表源生留空——工具會確定性反推",
        "     每張表的欄位去向（去到何處）。**欄名不必照抄來源**：可以取",
        "     比來源更有意義的名稱（命名依下方「命名決策順序」：字典標準詞",
        "     → 全碼全稱 → Common 命名規則；改名時 source 仍填來源的原欄名），",
        "     來源 → 新名的完整對應會自動渲染進 logical design 的",
        "     Column Mapping 節。",
        "     ⚠️ **名稱一致性會被驗證**：tables[].name 必須＝該表 ddl 的",
        "     CREATE TABLE 名、columns 宣告必須＝ddl 欄位集合、內部 source",
        "     必須指向真實存在的來源表.欄位——不一致設計稿會被退回。",
        "     **表間關係以 config 的 source table（權威來源）為對象**：",
        "     欄位 source 填三段式 `DOMAIN.table.col` 者，工具會**自動衍生**",
        "     對來源表的 N:1 reference 進 relations 草稿，**不必手填**；",
        "     `table_relations` 只需宣告**設計表之間真實的 FK／引用**",
        "     （from＝多的一方；格式同 relations.yaml）。",
        "     **跨表比對會自動檢查**：join 鍵兩端型別一致、引用欄與 source",
        "     型別相容（刻意轉型請在設計決策交代）、同名欄跨表型別一致、",
        "     同名非鍵欄跨表重複且無 source 血緣（重複承載風險）。",
        "     **每張表必附 `keys`（key 設計描述）**：business_key（業務唯一鍵，",
        "     一行的身分；欄位必須存在於 columns）、description（key 語意——",
        "     唯一性如何保證、與 ORDER BY 排序鍵的關係、去重策略；注意",
        "     ClickHouse 的 ORDER BY 不是唯一約束）、join_keys（選填：",
        "     對外 join 用哪個鍵、對到哪個權威）。",
        "     **每張表必附 design_decisions（設計決策與理由）**——為什麼選這個",
        "     ENGINE／ORDER BY／PARTITION／型別，取捨依據是什麼（對照設計約束",
        "     與參考模型）；文件會渲染成 Entity Overview（總覽）＋",
        "     Entity Detail（明細）兩節，key、血緣、決策與理由逐表呈現。",
        "   - **draft_ddl**：可執行的 ClickHouse CREATE TABLE 草稿（含每欄 COMMENT），",
        "     必須盡量符合下方「設計約束」列出的閘門規則——設計稿之後會用",
        "     同一套規則預檢。",
        "   - **narrative**（設計故事——給人讀的）：用**白話**說清楚整個設計",
        "     背後的原因與理由，讓工程師讀完能得到啟發：tldr（一句話總結）、",
        "     why（為什麼需要這個主體，業務動機白話版）、how_design_thinks",
        "     （設計思路：積木怎麼拆、粒度怎麼定、為什麼）、tradeoffs",
        "     （關鍵取捨：選了什麼、放棄了什麼、為什麼——誠實寫出代價）、",
        "     how_to_use（實用指南：常見使用場景該怎麼查、該 join 什麼、",
        "     指標怎麼算才對）、pitfalls（常見誤用與陷阱）、lessons",
        "     （這個設計示範了哪些可複用的 pattern）、references",
        "     （**設計出處**：哪個想法來自哪個 config 檔——對照下方素材清單",
        "     誠實列出，例如實體對齊了哪份參考模型、權威邊界依據哪份 SSOT）。",
        "   - **etl_pipeline**（選填、純建議）：未來系統內 ETL 需要的設定——",
        "     pipeline id、所屬 product suite、namespace、來源 DB／目標 DB、",
        "     用在哪個 database（ex: clickhouse）、更新方式",
        f"     （{'／'.join(etl_manifest.WRITE_MODES)}）、CPU／Memory 配置、",
        "     更新頻率、owner；逐表可用 `tables[]` 覆寫（`table` 必須是",
        "     physical_design 裡真實存在的表名）。**只填 context.md 或素材裡",
        "     真的講了的欄位，其餘一律省略、不要臆測**——工具會把沒給的欄位",
        f"     留成殼（`design_doc/{name}/{name}.etl.yaml`）並自動在設計問答請使用者填。",
        "     這份檔案與其他產物完全無關聯，不進閘門、不影響任何判定。",
        "   - **open_questions**：設計時拿不準、需要使用者決策的問題",
        "     （繁中提問語氣；已答／擱置的主題不得再以任何措辭重問）。",
        "     ETL 建議檔缺的欄位**不必**由你出題——工具已確定性產生對應提問。",
        f"2. 寫成 JSON：`design_doc/{name}/{name}.design_result.json`，格式見",
        "   `config/_engine/design_result.schema.json`，骨架：",
        "```json",
        json.dumps({
            "logical_design": {
                "business_context": "業務脈絡：這個 subject 為何存在、支撐什麼（繁中）",
                "domain_boundary": {
                    "statement": "邊界說明：本主體管什麼、不管什麼",
                    "owns": ["本主體擁有權威的事實"],
                    "references": [{"entity": "外部實體", "authority": "權威位置",
                                    "note": "只存鍵，不複製屬性"}],
                },
                "entities": [{"name": "實體名", "kind": "fact",
                              "description": "…", "grain": "一行代表什麼",
                              "attributes": [{"name": "屬性", "description": "…",
                                              "business_key": True}]}],
                "relationships": [{"from": "實體A", "to": "實體B",
                                   "cardinality": "N:1", "description": "…"}],
                "metric_contracts": [{"name": "指標名", "definition": "定義口徑",
                                      "grain": "彙總粒度", "source": "來源欄位",
                                      "caveats": "注意事項"}],
                "cross_domain_dependencies": [
                    {"domain": "CRM", "entity": "dim_customer",
                     "direction": "upstream", "via": "customer_id",
                     "description": "客戶主檔權威在 CRM；本主體只存鍵"}],
            },
            "physical_design": {
                "overview": "實作策略總覽（繁中；含積木分層的組合思路）",
                "tables": [{"name": "表名", "layer": "base|intermediate|wide",
                            "engine": "MergeTree()",
                            "order_by": "(id)", "partition_by": "",
                            "comment": "表用途",
                            "columns": [{"name": "欄", "type": "UInt64",
                                         "nullable": False, "comment": "…",
                                         "source": "來源表.欄位（本表源生留空）"}],
                            "ddl": "CREATE TABLE 表名 (…) ENGINE = …;",
                            "keys": {
                                "business_key": ["id"],
                                "description": "唯一性如何保證、與排序鍵的關係、"
                                               "去重策略",
                                "join_keys": [{"column": "外鍵欄",
                                               "references": "權威表.欄",
                                               "note": "…"}]},
                            "design_decisions": [
                                {"decision": "ORDER BY (id)",
                                 "rationale": "為什麼這樣選、取捨依據"}]}],
                "table_relations": [
                    {"from": "明細表.鍵", "to": "主表.鍵",
                     "cardinality": "N:1", "kind": "fk", "note": "…"}],
                "notes": ["跨表層級的設計注意事項"],
            },
            "narrative": {
                "tldr": "一句話總結這個設計",
                "why": "為什麼需要這個主體（業務動機，白話）",
                "how_design_thinks": "設計思路：積木怎麼拆、粒度怎麼定、為什麼",
                "tradeoffs": [{"chose": "選了什麼", "instead_of": "放棄了什麼",
                               "because": "為什麼（含代價）"}],
                "how_to_use": [{"scenario": "使用場景", "guidance": "該怎麼用"}],
                "pitfalls": ["常見誤用與陷阱"],
                "lessons": ["可複用的設計 pattern 啟發"],
                "references": [{"source": "config/<域>/erd/<檔>.md",
                                "how": "哪個設計想法來自這份 config"}],
            },
            "etl_pipeline": {
                "id": "ETL pipeline 識別碼（不知道就整個 key 省略）",
                "product_suite": "所屬 product suite",
                "namespace": "ETL 系統的命名空間",
                "platform": "用在哪個 database，ex: clickhouse",
                "source_db": "來源 DB", "target_db": "目標 DB",
                "write_mode": "|".join(etl_manifest.WRITE_MODES),
                "schedule": "更新頻率，ex: daily 02:00",
                "owner": "負責人或團隊",
                "resources": {"cpu": "2", "memory": "4Gi"},
                "tables": [{"table": "表名（須存在於 physical_design）",
                            "write_mode": "逐表覆寫（沒覆寫就沿用上面）"}],
            },
            "open_questions": [{"question": "給使用者的設計提問（繁中）",
                                "proposed_answer": "你代填的建議答案"}],
        }, ensure_ascii=False, indent=2),
        "```",
        "   **每題 open_question 都要附 `proposed_answer` 代填答案**——渲染時會",
        f"   寫進 `input/{name}/design_answers.yaml` 標 `status: proposed`",
        "   （待驗證），由使用者驗證（改 answered／deferred）後，下一輪自動",
        "   帶入 prompt。你不得自行把 proposed 改成 answered。",
        f"3. 重跑 `python run.py {name}` → 工具會確定性渲染",
        f"   `design_doc/{name}/{name}.logical_design.md`、`{name}.physical_design.md`、",
        f"   `{name}.design.sql`、`{name}.etl.yaml`（ETL 建議檔），",
        "   並對 draft_ddl 做閘門預檢、記錄設計輪次。",
        "4. 向使用者回報：第幾輪設計、預檢結果、open_questions，並提醒——",
        f"   設計定稿後由**使用者**把 design.sql 存成 `input/{name}/{name}.sql`",
        "   （＋補 relations.yaml）進入 govern mode；agent 不得代寫權威輸入。", "",
        "## context.md（唯一的語意輸入）", "",
        "```markdown", context_text.strip(), "```", "",
        f"（front-matter 解析：subject=`{meta.get('subject', '')}`、"
        f"domains={domains or '[]'}、business_keys="
        f"{meta.get('business_keys') or '{}'}）", "",
    ]
    state = qa_state(answers or {})
    lines += ["## 已澄清的設計問答（使用者已驗證——勿重問，依答案修設計）", ""]
    if state["answered"]:
        for entry in state["answered"]:
            lines += [f"- **Q**：{entry.get('question', '')}",
                      f"  **A**：{entry.get('answer', '')}"]
    else:
        lines.append("（無——本輪尚無已驗證的設計問答）")
    if state["deferred"]:
        lines += ["", "## 擱置的設計問答（使用者不追了——勿重問）", ""]
        lines += [f"- {e.get('question', '')}" for e in state["deferred"]]
    # 表命名前綴：context 宣告 product 時，表名帶產品縮寫
    products = load_products(config_dir, domains)
    declared_code = str(meta.get("product") or "").strip().lower()
    layers = list(products["layers"]) or ["ods", "dim", "dwd", "dws", "ads"]
    layer_desc = "、".join(f"`{k}`（{v}）" for k, v in
                           (products["layers"] or
                            {"ods": "原始層", "dim": "維度表",
                             "dwd": "明細事實", "dws": "彙總層",
                             "ads": "應用層"}).items())
    lines += ["", "## 表命名前綴（產品縮寫）", ""]
    if declared_code and declared_code in products["codes"]:
        info = products["codes"][declared_code]
        lines += [f"本 subject 宣告產品：`{declared_code}`"
                  f"（{info.get('name', '')}，登錄於 config/"
                  f"{info.get('domain', '')}/products/）。",
                  f"**表名一律**：`<分層前綴>_{declared_code}_<語意名>`——"
                  f"例：`dim_{declared_code}_customer`、"
                  f"`dwd_{declared_code}_order`。",
                  f"分層前綴：{layer_desc}。工具會逐表檢查此格式。"]
    elif declared_code:
        lines += [f"⚠️ context 宣告的產品縮寫 `{declared_code}` **未登錄**於 "
                  "config/<域>/products/registry.md——表名仍請依 "
                  f"`<分層前綴>_{declared_code}_<語意名>` 命名，並在 "
                  "open_questions 提議把此縮寫登錄進註冊表"
                  "（proposed_answer 附產品名稱）。"]
    else:
        lines += ["（context 未宣告 `product`——表名不強制產品前綴。若本 "
                  "subject 屬於某產品，請使用者在 context.md front-matter 加 "
                  "`product: <縮寫>`；可用縮寫見 config/<域>/products/"
                  "registry.md。）"]
    lines += ["", "## 命名決策順序（表名／欄名的命名依據，依序套用）", "",
              "1. **詞彙字典有登錄** → 一律用字典的標準詞（別名／禁用縮寫",
              "   一律換成右欄的正規詞；字典全文見下方素材）。",
              "2. **字典沒有的概念** → 用**全碼**（完整拼寫的英文全稱），",
              "   **不得自創縮寫**（cust／qty 這類縮寫即使字典漏列也不可用），",
              "   並在 open_questions 提議把新詞登錄進字典",
              "   （proposed_answer 附建議詞條：`新詞 → 建議標準詞`），",
              "   讓字典隨設計一起長大。",
              "3. **命名形式**一律依 Common 命名規則為參考依據：snake_case",
              "   全小寫、主鍵以 `_id` 結尾、表名 ≤64／欄名 ≤48 字元、",
              "   避開 SQL 保留字——這些同時是閘門會實檢的規則",
              "   （見下方設計約束）。", ""]
    lines += ["", "## 正式區資產（必讀——先複用，不要重造）", "",
              "`config/Common/production/registry.md` 列出所有**已核准上線**的",
              "data subject（每次起跑自動更新）。起草前先讀它：你要承載的事實",
              "如果正式區已經有了，**引用它**而不是在本主體重建一份——",
              "欄位 `source` 填三段式 `DOMAIN.table.col`，工具會自動衍生對來源",
              "表的 relation，不必手填。引用只存鍵，不要複製外部權威的屬性。",
              "確認過真的沒有可複用的，也請在 open_questions 交代原因",
              "（沒有任何引用時，工具會另外產一題請使用者確認）。", ""]
    lines += ["## 設計約束（閘門規則——draft_ddl 之後要過這些）", ""]
    lines += _gating_constraints(compiled_path, domains)
    lines += ["", "## 設計 know-how（顧問區語意準則——起草時據以自我檢視）", "",
              "這些準則不擋、但描述「好設計長什麼樣」；設計時先對齊，",
              "定稿進治理後顧問區的提問就會少很多。", ""]
    lines += _advisory_knowhow(compiled_path, domains)
    # 素材呈現模式：index（預設）＝目錄＋按需開檔，agent context 最小；
    # full＝全文 inline（回退用）。DATAVAL_DESIGN_PROMPT 可切換。
    mode = (material_mode or
            os.environ.get("DATAVAL_DESIGN_PROMPT", "index")).strip().lower()
    if mode == "full":
        lines += ["", "## 參考模型素材（宣告 domain ＋ Common）", ""]
        lines += _reference_sections(config_dir, domains)
    else:
        lines += ["", "## 參考模型素材索引（宣告 domain ＋ Common；"
                  "按需開檔）", ""]
        lines += _reference_index_lines(config_dir, domains)
    return "\n".join(lines) + "\n"


def index_review_md(config_dir: str) -> str:
    """索引草稿審閱表（全 config，自動產生）：給維護者的 curation 狀態板。
    維護介面刻意極簡——三個選填欄位寫在素材檔自己的 front-matter，
    不填就用 🤖 自動摘要與預設值，隨時補、補多少算多少。"""
    domains = sorted(f for f in os.listdir(config_dir)
                     if os.path.isdir(os.path.join(config_dir, f))
                     and not f.startswith("_") and f.lower() != "common")
    entries = design_index(config_dir, domains)
    lines = ["# 設計素材索引 — 審閱表（自動產生，勿手改本檔）", "",
             "**怎麼維護（只有三個選填欄位）**：打開想調整的素材檔，"
             "在檔案最上方加（或補）front-matter——", "",
             "```yaml", "---",
             "index_summary: 一句話說明這份素材（覆蓋 🤖 自動摘要）",
             "index_stage: [L]        # L＝logical 起草要看；P＝physical/DDL 才要看",
             "index_required: true    # 必讀：設計出處漏引用會被提醒",
             "---", "```", "",
             "不填也能用（自動摘要＋預設階段）；存檔後下次 run.py 生效。", "",
             "| 素材 | 路徑 | 摘要 | 階段 | 必讀 | 狀態 |",
             "|---|---|---|---|---|---|"]
    for e in entries:
        lines.append(
            f"| {e['kind']} | `{e['path']}` | {e['summary']} "
            f"| {','.join(e['stage'])} "
            f"| {'✅' if e['required'] else '—'} "
            f"| {'🤖 自動（待人工確認）' if e['auto_summary'] else '✍️ 已人工維護'} |")
    lines += ["", f"共 {len(entries)} 份素材。🤖 表示摘要為自動萃取——"
              "有空逐條補 front-matter 即可，一次補幾條都行。", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- 積木與血緣

#: 積木層級：小積木（base 源頭表）／中積木（intermediate 組合表）／寬表（wide）
LAYERS = ("base", "intermediate", "wide")
LAYER_LABEL = {"base": "小積木（base）", "intermediate": "中積木（intermediate)",
               "wide": "寬表（wide）"}
_SRC_RE = re.compile(r"^([A-Za-z_]\w*)\.([A-Za-z_]\w*)$")
#: 依據文字裡的具體 config 路徑（含佔位符的不成連結）
_ORIGIN_PATH_RE = re.compile(r"config/[A-Za-z0-9_\-./]+")


def _origin_md(text: str) -> str:
    """依據文字 → Markdown：具體 config/ 路徑轉相對連結
    （設計文件在 design_doc/<名>/，往上兩層直達實際規則檔）。"""
    return _ORIGIN_PATH_RE.sub(
        lambda m: (m.group(0) if m.group(0) == "config/"
                   else f"[{m.group(0)}]({docpaths.ROOT_PREFIX}{m.group(0)})"),
        text)


def combined_ddl(result: dict) -> str:
    """全部設計 DDL 合併文字：各表 ddl 依宣告順序串接；
    沒有逐表 ddl 時退回單檔 draft_ddl（相容舊格式）。"""
    tables = (result.get("physical_design") or {}).get("tables") or []
    parts = [str(t.get("ddl", "")).strip() for t in tables
             if str(t.get("ddl", "")).strip()]
    if parts:
        return "\n\n".join(parts)
    return str(result.get("draft_ddl", "")).strip()


def downstream_edges(tables: list) -> dict[str, list[str]]:
    """欄位去向（確定性推導）：掃全部表的 column.source，
    反向整理出「本表.欄 → 下游表.欄」。key＝來源表名。"""
    edges: dict[str, list[str]] = {}
    for t in tables:
        tname = str(t.get("name", ""))
        for c in t.get("columns") or []:
            m = _SRC_RE.match(str(c.get("source", "")).strip())
            if m:
                edges.setdefault(m.group(1), []).append(
                    f"`{m.group(1)}.{m.group(2)}` → `{tname}.{c.get('name', '')}`")
    return edges


# ---------------------------------------------------------------- result 驗證

def validate_design_result(result) -> list[str]:
    """驗證 design_result 的結構（無外部依賴；語意由渲染與預檢把關）。"""
    errors: list[str] = []
    if not isinstance(result, dict):
        return ["最外層必須是 JSON object"]
    required = {"logical_design", "physical_design", "narrative"}
    optional = {"open_questions", "draft_ddl", "etl_pipeline"}
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
        # 六節缺一不可：business_context／domain_boundary／entities
        # （Overview＋Detail 由 entities 渲染）／relationships／
        # metric_contracts／cross_domain_dependencies
        if not str(logical.get("business_context", "")).strip():
            errors.append("logical_design.business_context 必須是非空字串")
        boundary = logical.get("domain_boundary")
        if not isinstance(boundary, dict) or \
                not str(boundary.get("statement", "")).strip():
            errors.append("logical_design.domain_boundary 必須是 object 且含"
                          "非空 statement")
        entities = logical.get("entities")
        if not isinstance(entities, list) or not entities:
            errors.append("logical_design.entities 必須是非空 array")
        else:
            for i, ent in enumerate(entities):
                if not isinstance(ent, dict) or not str(ent.get("name", "")).strip():
                    errors.append(f"logical_design.entities[{i}] 必須含非空 name")
        if not isinstance(logical.get("relationships", []), list):
            errors.append("logical_design.relationships 必須是 array")
        contracts = logical.get("metric_contracts")
        if not isinstance(contracts, list):
            errors.append("logical_design.metric_contracts 必須是 array"
                          "（沒有指標承諾時給空 array）")
        else:
            for i, mc in enumerate(contracts):
                if not isinstance(mc, dict) or \
                        not str(mc.get("name", "")).strip() or \
                        not str(mc.get("definition", "")).strip():
                    errors.append(f"logical_design.metric_contracts[{i}] "
                                  "必須含非空 name 與 definition")
        deps = logical.get("cross_domain_dependencies")
        if not isinstance(deps, list):
            errors.append("logical_design.cross_domain_dependencies 必須是 "
                          "array（無跨域依賴時給空 array）")
        else:
            for i, dep in enumerate(deps):
                if not isinstance(dep, dict) or \
                        not str(dep.get("domain", "")).strip() or \
                        not str(dep.get("entity", "")).strip():
                    errors.append(
                        f"logical_design.cross_domain_dependencies[{i}] "
                        "必須含非空 domain 與 entity")

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
                    continue
                if not isinstance(table.get("columns", []), list):
                    errors.append(f"physical_design.tables[{i}].columns 必須是 array")
                layer = table.get("layer")
                if layer is not None and layer not in LAYERS:
                    errors.append(f"physical_design.tables[{i}].layer 限 "
                                  f"{'|'.join(LAYERS)}")
                for j, c in enumerate(table.get("columns") or []):
                    if isinstance(c, dict) and \
                            not isinstance(c.get("source", ""), str):
                        errors.append(f"physical_design.tables[{i}]."
                                      f"columns[{j}].source 必須是字串")
                if not isinstance(table.get("ddl", ""), str):
                    errors.append(f"physical_design.tables[{i}].ddl 必須是字串")
                # key 設計描述：business_key＋語意說明，欄位必須真的存在
                keys = table.get("keys")
                if not isinstance(keys, dict):
                    errors.append(f"physical_design.tables[{i}].keys 必須是 "
                                  "object（business_key＋description）")
                else:
                    bk = keys.get("business_key")
                    col_names = {str(c.get("name", "")).lower()
                                 for c in table.get("columns") or []
                                 if isinstance(c, dict)}
                    if not isinstance(bk, list) or not bk or \
                            any(not str(x).strip() for x in bk):
                        errors.append(f"physical_design.tables[{i}].keys."
                                      "business_key 必須是非空欄位 list")
                    elif col_names:
                        missing_cols = [str(x) for x in bk
                                        if str(x).lower() not in col_names]
                        if missing_cols:
                            errors.append(
                                f"physical_design.tables[{i}].keys."
                                f"business_key 欄位不存在於 columns："
                                f"{missing_cols}")
                    if not str(keys.get("description", "")).strip():
                        errors.append(f"physical_design.tables[{i}].keys."
                                      "description 必須是非空字串"
                                      "（唯一性語意與去重策略）")
                    jks = keys.get("join_keys")
                    if jks is not None:
                        if not isinstance(jks, list):
                            errors.append(f"physical_design.tables[{i}].keys."
                                          "join_keys 必須是 array")
                        else:
                            for j, jk in enumerate(jks):
                                if not isinstance(jk, dict) or \
                                        not str(jk.get("column", "")).strip():
                                    errors.append(
                                        f"physical_design.tables[{i}].keys."
                                        f"join_keys[{j}] 必須含非空 column")
                # 每張表必附設計決策與理由（Entity Detail 逐表呈現）
                decisions = table.get("design_decisions")
                if not isinstance(decisions, list) or not decisions:
                    errors.append(f"physical_design.tables[{i}].design_decisions "
                                  "必須是非空 array（每張表都要有設計決策與理由）")
                else:
                    for j, d in enumerate(decisions):
                        if not isinstance(d, dict) or \
                                not str(d.get("decision", "")).strip() or \
                                not str(d.get("rationale", "")).strip():
                            errors.append(
                                f"physical_design.tables[{i}]."
                                f"design_decisions[{j}] 必須含非空 decision "
                                "與 rationale")

        # 表間關係（渲染成 relations 草稿；定稿時可直接沿用）
        rels = physical.get("table_relations")
        if rels is not None:
            if not isinstance(rels, list):
                errors.append("physical_design.table_relations 必須是 array")
            else:
                for i, rel in enumerate(rels):
                    if not isinstance(rel, dict) or \
                            not str(rel.get("from", "")).strip() or \
                            not str(rel.get("to", "")).strip():
                        errors.append(f"physical_design.table_relations[{i}] "
                                      "必須含非空 from 與 to")
                    elif rel.get("cardinality") not in (None, "", "1:1",
                                                        "N:1", "N:M"):
                        errors.append(f"physical_design.table_relations[{i}]"
                                      ".cardinality 限 1:1|N:1|N:M")
    if not combined_ddl(result):
        errors.append("設計 DDL 不可為空：每張表附 ddl（建議，逐表拆檔），"
                      "或提供整體 draft_ddl（相容單檔）")
    errors += _consistency_errors(result)
    narrative = result.get("narrative")
    if not isinstance(narrative, dict):
        errors.append("narrative 必須是 object（設計故事——給人讀的）")
    else:
        for key in ("tldr", "why"):
            if not str(narrative.get(key, "")).strip():
                errors.append(f"narrative.{key} 必須是非空字串")
        tradeoffs = narrative.get("tradeoffs")
        if not isinstance(tradeoffs, list) or not tradeoffs:
            errors.append("narrative.tradeoffs 必須是非空 array"
                          "（誠實寫出設計取捨與代價）")
        else:
            for i, tr in enumerate(tradeoffs):
                if not isinstance(tr, dict) or \
                        not str(tr.get("chose", "")).strip() or \
                        not str(tr.get("because", "")).strip():
                    errors.append(f"narrative.tradeoffs[{i}] 必須含非空 "
                                  "chose 與 because")
        usages = narrative.get("how_to_use")
        if not isinstance(usages, list) or not usages:
            errors.append("narrative.how_to_use 必須是非空 array（實用指南）")
        else:
            for i, u in enumerate(usages):
                if not isinstance(u, dict) or \
                        not str(u.get("scenario", "")).strip() or \
                        not str(u.get("guidance", "")).strip():
                    errors.append(f"narrative.how_to_use[{i}] 必須含非空 "
                                  "scenario 與 guidance")
        for key in ("pitfalls", "lessons"):
            value = narrative.get(key)
            if value is not None and (
                    not isinstance(value, list) or
                    any(not isinstance(x, str) for x in value)):
                errors.append(f"narrative.{key} 必須是字串 array")
        refs = narrative.get("references")
        if refs is not None:
            if not isinstance(refs, list):
                errors.append("narrative.references 必須是 array（設計出處）")
            else:
                for i, ref in enumerate(refs):
                    if not isinstance(ref, dict) or \
                            not str(ref.get("source", "")).strip() or \
                            not str(ref.get("how", "")).strip():
                        errors.append(f"narrative.references[{i}] 必須含非空 "
                                      "source 與 how")
    oq = result.get("open_questions")
    if oq is not None:
        if not isinstance(oq, list):
            errors.append("open_questions 必須是 array")
        else:
            for i, q in enumerate(oq):
                if isinstance(q, str):
                    continue  # 純字串相容（建議改用 object 附 proposed_answer）
                if not isinstance(q, dict) or \
                        not str(q.get("question", "")).strip():
                    errors.append(f"open_questions[{i}] 必須是字串或含非空 "
                                  "question 的 object")
                elif not isinstance(q.get("proposed_answer", ""), str):
                    errors.append(f"open_questions[{i}].proposed_answer "
                                  "必須是字串")
    # ETL 建議檔的設定（選填；沒給就整段省略，工具會長殼並在問答區問）
    errors += etl_manifest.validate(result)
    return errors


def _consistency_errors(result: dict) -> list[str]:
    """名稱一致性（確定性交叉檢查）：physical_design 宣告是所有產物的根
    （報告、拆檔名、問答都從它衍生），必須與 DDL 實際內容完全一致。

      C1 逐表 ddl 可解析，且 CREATE TABLE 名稱＝tables[].name
      C2 逐表 ddl 的欄位集合＝tables[].columns 宣告（文件不得與 DDL 漂移）
      C3 單檔 draft_ddl 模式：解析出的表名集合＝tables[].name 集合
      C4 欄位 source 指向設計內的表時，來源表.欄位必須真實存在（抓改名筆誤）
    """
    errors: list[str] = []
    physical = result.get("physical_design")
    if not isinstance(physical, dict):
        return errors
    tables = [t for t in physical.get("tables") or []
              if isinstance(t, dict) and str(t.get("name", "")).strip()]
    declared_cols: dict[str, set[str]] = {}
    for t in tables:
        declared_cols[str(t["name"]).lower()] = {
            str(c.get("name", "")).lower() for c in t.get("columns") or []
            if isinstance(c, dict)}
    has_per_table_ddl = any(str(t.get("ddl", "")).strip() for t in tables)
    if has_per_table_ddl:
        for t in tables:
            name = str(t["name"])
            ddl = str(t.get("ddl", "")).strip()
            if not ddl:
                errors.append(f"表 `{name}` 缺 ddl（其他表有逐表 ddl 時"
                              "不得混用單檔模式）")
                continue
            try:
                parsed = parse_ddl(ddl).tables
            except Exception as e:
                errors.append(f"表 `{name}` 的 ddl 無法解析："
                              f"{type(e).__name__}: {e}")
                continue
            if len(parsed) != 1:
                errors.append(f"表 `{name}` 的 ddl 必須恰含一張 CREATE TABLE"
                              f"（實得 {len(parsed)}）")
                continue
            actual = parsed[0].name
            if actual.lower() != name.lower():
                errors.append(f"表名不一致：physical_design 宣告 `{name}`，"
                              f"ddl 實際是 `{actual}`——報告／拆檔名／問答都以"
                              "宣告為準，兩者必須相同")
                continue
            ddl_cols = {c.name.lower() for c in parsed[0].columns}
            doc_cols = declared_cols[name.lower()]
            missing = sorted(doc_cols - ddl_cols)
            extra = sorted(ddl_cols - doc_cols)
            if missing or extra:
                errors.append(f"表 `{name}` 的欄位宣告與 ddl 不一致："
                              f"文件有 ddl 沒有 {missing or '（無）'}；"
                              f"ddl 有文件沒有 {extra or '（無）'}")
    else:
        draft = str(result.get("draft_ddl", "")).strip()
        if draft:
            try:
                parsed_names = {t.name.lower()
                                for t in parse_ddl(draft).tables}
            except Exception as e:
                errors.append(f"draft_ddl 無法解析：{type(e).__name__}: {e}")
                parsed_names = None
            if parsed_names is not None and \
                    parsed_names != set(declared_cols):
                errors.append(
                    "draft_ddl 的表名集合與 physical_design.tables 宣告"
                    f"不一致：DDL {sorted(parsed_names)} ↔ 宣告 "
                    f"{sorted(declared_cols)}")
    # C5：table_relations 本地端點必須真實存在（表與欄位）
    rels = physical.get("table_relations") or []
    for i, rel in enumerate(rels if isinstance(rels, list) else []):
        if not isinstance(rel, dict):
            continue
        for end in ("from", "to"):
            m = _SRC_RE.match(str(rel.get(end, "")).strip())
            if not m:
                continue   # 外部三段式端點或格式錯誤（另有檢查）
            tbl, col = m.group(1).lower(), m.group(2).lower()
            if tbl in declared_cols and col not in declared_cols[tbl]:
                errors.append(f"table_relations[{i}].{end} 指向不存在的欄位："
                              f"`{m.group(1)}.{m.group(2)}`")
    # C4：內部 source 必須指向真實存在的 來源表.欄位
    for t in tables:
        for c in t.get("columns") or []:
            if not isinstance(c, dict):
                continue
            m = _SRC_RE.match(str(c.get("source", "")).strip())
            if not m:
                continue
            src_table, src_col = m.group(1).lower(), m.group(2).lower()
            if src_table in declared_cols and \
                    src_col not in declared_cols[src_table]:
                errors.append(
                    f"欄位 `{t['name']}.{c.get('name', '')}` 的 source "
                    f"`{m.group(1)}.{m.group(2)}` 不存在——來源表 "
                    f"`{m.group(1)}` 沒有欄位 `{m.group(2)}`（改名時 source "
                    "要填來源的原欄名）")
    return errors


def _norm_type(t: str) -> str:
    return re.sub(r"\s+", "", str(t)).lower()


def _base_type(t: str) -> str:
    """型別比對用：剝掉 Nullable() 外殼（Nullable 差異另屬設計語意）。"""
    m = re.match(r"^nullable\((.*)\)$", _norm_type(t))
    return m.group(1) if m else _norm_type(t)


def cross_table_checks(result: dict) -> list[dict]:
    """設計內跨表比對（確定性、零 LLM）：多張積木之間的一致性。

      X1 join 鍵型別一致：table_relations 本地兩端的欄位型別相容
      X2 source 型別相容：改名不改義——來源欄與本欄型別一致（轉型要交代）
      X3 同名欄位跨表型別一致：同名欄（如稽核欄）在各表型別必須相同
      X4 重複承載偵測：同名非鍵欄跨表存在、卻無 source 血緣宣告
         → 可能是同一事實散落多表（SSOT 風險），設計階段先顯性化

    回傳 [{check, status: pass|warn|fail, detail}]；單表設計回空 list。"""
    physical = result.get("physical_design") or {}
    tables = [t for t in physical.get("tables") or []
              if isinstance(t, dict) and str(t.get("name", "")).strip()]
    if len(tables) < 2:
        return []
    names = {str(t["name"]).lower(): str(t["name"]) for t in tables}
    cols = {str(t["name"]).lower():
            {str(c.get("name", "")).lower(): str(c.get("type", ""))
             for c in t.get("columns") or [] if isinstance(c, dict)}
            for t in tables}
    out: list[dict] = []

    # X1 join 鍵型別一致
    checked, bad = 0, []
    for rel in physical.get("table_relations") or []:
        if not isinstance(rel, dict):
            continue
        mf = _SRC_RE.match(str(rel.get("from", "")).strip())
        mt = _SRC_RE.match(str(rel.get("to", "")).strip())
        if not (mf and mt):
            continue
        ft, fc = mf.group(1).lower(), mf.group(2).lower()
        tt, tc = mt.group(1).lower(), mt.group(2).lower()
        if ft not in cols or tt not in cols:
            continue    # 外部端點不在設計內
        ftype, ttype = cols[ft].get(fc), cols[tt].get(tc)
        if ftype is None or ttype is None:
            continue    # 端點不存在（C5 已擋）
        checked += 1
        if _base_type(ftype) != _base_type(ttype):
            bad.append(f"`{rel['from']}`（{ftype}） ↔ `{rel['to']}`（{ttype}）")
    if checked:
        out.append({"check": "X1 join 鍵型別一致（table_relations 兩端）",
                    "status": "fail" if bad else "pass",
                    "detail": "；".join(bad)
                    or f"{checked} 組 join 鍵型別皆相容"})

    # X2 source 型別相容
    checked, bad = 0, []
    for t in tables:
        for c in t.get("columns") or []:
            if not isinstance(c, dict):
                continue
            m = _SRC_RE.match(str(c.get("source", "")).strip())
            if not m:
                continue
            st, sc = m.group(1).lower(), m.group(2).lower()
            if st not in cols or sc not in cols[st]:
                continue    # C4 已擋
            checked += 1
            if _base_type(cols[st][sc]) != _base_type(str(c.get("type", ""))):
                bad.append(f"`{t['name']}.{c.get('name', '')}`"
                           f"（{c.get('type', '')}）← `{m.group(1)}."
                           f"{m.group(2)}`（{cols[st][sc]}）")
    if checked:
        out.append({"check": "X2 source 型別相容（改名不改義；刻意轉型請在"
                             "設計決策交代）",
                    "status": "warn" if bad else "pass",
                    "detail": "；".join(bad)
                    or f"{checked} 個引用欄與來源型別皆一致"})

    # 同名欄位的跨表分布
    by_col: dict[str, dict[str, str]] = {}
    for tl, cc in cols.items():
        for cl, tp in cc.items():
            by_col.setdefault(cl, {})[tl] = tp

    # X3 同名欄位跨表型別一致
    shared = {cl: owners for cl, owners in by_col.items() if len(owners) > 1}
    bad = []
    for cl, owners in sorted(shared.items()):
        if len({_base_type(tp) for tp in owners.values()}) > 1:
            bad.append(f"`{cl}`：" + "、".join(
                f"{names[tl]}={tp}" for tl, tp in sorted(owners.items())))
    out.append({"check": "X3 同名欄位跨表型別一致",
                "status": "fail" if bad else "pass",
                "detail": "；".join(bad)
                or (f"{len(shared)} 個同名欄位型別皆一致"
                    if shared else "無跨表同名欄位")})

    # X4 重複承載（同名非鍵欄、跨表存在、無 source 血緣）
    audit = {"created_at", "updated_at"}
    bk = {str(x).lower() for t in tables
          for x in (t.get("keys") or {}).get("business_key") or []}
    bad = []
    for cl, owners in sorted(shared.items()):
        if cl in audit or cl in bk or cl.endswith("_id"):
            continue
        linked = False
        for t in tables:
            if str(t["name"]).lower() not in owners:
                continue
            for c in t.get("columns") or []:
                if not isinstance(c, dict) or \
                        str(c.get("name", "")).lower() != cl:
                    continue
                m = _SRC_RE.match(str(c.get("source", "")).strip())
                if m and m.group(1).lower() in owners:
                    linked = True
        if not linked:
            bad.append(f"`{cl}`（" + "、".join(
                sorted(names[tl] for tl in owners)) + "）")
    out.append({"check": "X4 同一事實重複承載（同名欄跨表、無 source 血緣）",
                "status": "warn" if bad else "pass",
                "detail": ("；".join(bad) + "——若是刻意冗餘請補 source 宣告"
                           "血緣，否則收斂到單一權威表")
                if bad else "無未宣告血緣的跨表重複欄位"})
    return out


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


def latest_round_result(history_root: str, subject: str) -> dict | None:
    """subject 的設計最終輪快照（round json 全文；含 result 與 round）。
    無設計歷史回 None——govern mode 據此決定建議 DDL 用設計稿還是參考模型。"""
    dirp = _design_dir(history_root, subject)
    rounds = _recorded_rounds(dirp)
    if not rounds:
        return None
    return _load_round(dirp, rounds[-1])


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
            combined_ddl(result).splitlines(),
            fromfile=f"第{rounds[-1]}輪設計", tofile=f"第{round_no}輪設計",
            lineterm=""))
        if len(diff_lines) > DIFF_MAX_LINES:
            diff_lines = diff_lines[:DIFF_MAX_LINES] + ["…（diff 過長截斷）"]
        ddl_diff = "\n".join(diff_lines)
    payload = {"format": FORMAT, "subject": subject, "round": round_no,
               **digest, "draft_ddl": combined_ddl(result),
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

def _logical_md(name: str, round_no: int, result: dict,
                answers: dict | None = None) -> str:
    logical = result.get("logical_design") or {}
    lines = [f"# 邏輯設計（Logical Design）— {name}（第 {round_no} 輪設計）", "",
             "> 🎨 design mode 產物：由 `context.md` 與參考模型起草（agent LLM），",
             "> 設計歷史見 `iterations/<名>/design/HISTORY.md`。定稿與否由使用者決定。",
             ""]
    # 1. Business Context
    lines += ["## 1. Business Context（業務脈絡）", "",
              str(logical.get("business_context", "")).strip() or "（無）", ""]
    # 2. Domain Boundary
    boundary = logical.get("domain_boundary") or {}
    lines += ["## 2. Domain Boundary（領域邊界）", "",
              str(boundary.get("statement", "")).strip() or "（無）"]
    if boundary.get("owns"):
        lines.append("- **本主體擁有的權威事實**："
                     + "、".join(str(x) for x in boundary["owns"]))
    refs = boundary.get("references") or []
    if refs:
        lines += ["", "| 引用的外部實體 | 權威位置 | 備註 |", "|---|---|---|"]
        lines += [f"| `{r.get('entity', '')}` | {r.get('authority', '')} "
                  f"| {r.get('note', '')} |" for r in refs]
    lines.append("")
    # 3. Entity Overview（含關係）
    entities = logical.get("entities") or []
    lines += ["## 3. Entity Overview（實體總覽）", "",
              "| 實體 | 類型 | 粒度 | Business Key | 說明 |",
              "|---|---|---|---|---|"]
    for ent in entities:
        bk = "、".join(f"`{a.get('name', '')}`"
                       for a in (ent.get("attributes") or [])
                       if a.get("business_key"))
        lines.append(f"| `{ent.get('name', '?')}` | {ent.get('kind', '')} "
                     f"| {ent.get('grain', '')} | {bk} "
                     f"| {str(ent.get('description', '')).strip()} |")
    rels = logical.get("relationships") or []
    lines += ["", "**實體關係**", ""]
    if rels:
        lines += ["| from | to | 基數 | 說明 |", "|---|---|---|---|"]
        lines += [f"| `{r.get('from', '')}` | `{r.get('to', '')}` "
                  f"| {r.get('cardinality', '')} | {r.get('description', '')} |"
                  for r in rels]
    else:
        lines.append("（無）")
    # 4. Entity Detail
    lines += ["", "## 4. Entity Detail（實體明細）"]
    for ent in entities:
        lines += ["", f"### {ent.get('name', '?')}"
                  + (f"（{ent.get('kind')}）" if ent.get("kind") else ""),
                  str(ent.get("description", "")).strip()]
        if ent.get("grain"):
            lines.append(f"- **粒度**：{ent['grain']}")
        attrs = ent.get("attributes") or []
        if attrs:
            lines += ["", "| 屬性 | 說明 | Business Key |", "|---|---|---|"]
            lines += [f"| `{a.get('name', '')}` | {a.get('description', '')} "
                      f"| {'✅' if a.get('business_key') else ''} |"
                      for a in attrs]
    # 5. Metric Contracts
    contracts = logical.get("metric_contracts") or []
    lines += ["", "## 5. Metric Contracts（指標契約）", ""]
    if contracts:
        lines += ["| 指標 | 定義口徑 | 粒度 | 來源 | 注意事項 |",
                  "|---|---|---|---|---|"]
        lines += [f"| **{m.get('name', '')}** | {m.get('definition', '')} "
                  f"| {m.get('grain', '')} | {m.get('source', '')} "
                  f"| {m.get('caveats', '')} |" for m in contracts]
    else:
        lines.append("（本主體未對下游承諾指標）")
    # 6. Cross Domain Dependency
    deps = logical.get("cross_domain_dependencies") or []
    lines += ["", "## 6. Cross Domain Dependency（跨域依賴）", ""]
    if deps:
        lines += ["| Domain | 實體 | 方向 | 介接鍵 | 說明 |",
                  "|---|---|---|---|---|"]
        lines += [f"| `{d.get('domain', '')}` | `{d.get('entity', '')}` "
                  f"| {d.get('direction', '')} | `{d.get('via', '')}` "
                  f"| {d.get('description', '')} |" for d in deps]
    else:
        lines.append("（無跨域依賴）")
    # 7. Column Mapping（欄位來源對應——改名詳實交代：source 的哪個欄位
    # 變成本設計的什麼欄位；確定性渲染自 physical 的 source 宣告）
    mapping_rows = []
    for t in (result.get("physical_design") or {}).get("tables") or []:
        for c in t.get("columns") or []:
            src = str(c.get("source", "")).strip()
            if not src:
                continue
            new_name = str(c.get("name", ""))
            if src.lower().startswith("expression"):
                mark = "🧮 運算欄"
            else:
                last = src.split(".")[-1].strip()
                mark = ("✏️ 改名" if last and last.lower() != new_name.lower()
                        else "—")
            mapping_rows.append(
                f"| `{src}` | `{t.get('name', '')}.{new_name}` | {mark} "
                f"| {str(c.get('comment', '')).strip()} |")
    lines += ["", "## 7. Column Mapping（欄位來源對應）", ""]
    if mapping_rows:
        lines += ["來源欄位 → 本設計欄位的完整對應。欄名可以取得比來源更有"
                  "意義（✏️＝已改名）；🧮＝運算欄。", "",
                  "| 來源（source） | 本設計欄位 | 改名 | 說明 |",
                  "|---|---|---|---|"]
        lines += mapping_rows
    else:
        lines.append("（沒有宣告 source 的欄位——全部為本設計源生）")
    oq = result.get("open_questions") or []
    by_id = {str(e.get("id", "")): e
             for e in (answers or {}).get("answers") or []
             if isinstance(e, dict)}
    status_label = {"proposed": "⏳ 待驗證（代填答案見 design_answers.yaml）",
                    "answered": "✅ 已答", "deferred": "⏸ 擱置"}
    lines += ["", f"## 設計問答（驗證：`input/{name}/design_answers.yaml` "
              "把 proposed 改 answered／deferred）", ""]
    if oq:
        for q in oq:
            text = question_text(q).strip()
            entry = by_id.get(question_id(text))
            status = str(entry.get("status", "proposed")) if entry else "proposed"
            lines.append(f"- {text}")
            lines.append(f"  - {status_label.get(status, status)}"
                         + (f"；答案：{entry.get('answer', '')}"
                            if entry and status == "answered" else ""))
    else:
        lines.append("（無）")
    return "\n".join(lines) + "\n"


def _etl_md(name: str, manifest: dict | None) -> list[str]:
    """ETL 建議檔的填寫狀態（獨立的建議產物，與合規判定無關）。"""
    if not manifest:
        return []
    info = etl_manifest.summary(manifest)
    lines = ["", f"## ETL Pipeline 建議檔（`design_doc/{name}/{name}.etl.yaml`）", "",
             "> 未來系統內 ETL 需要的設定（product suite／namespace／來源與目標 "
             "DB／更新方式／資源配置／頻率／owner）。**純建議檔**：與其他設計"
             "產物沒有關聯，不進閘門、不影響任何判定；沒有資訊的欄位會留殼"
             "（值留空＋標 TODO）並在設計問答請使用者填。", "",
             f"pipeline 層欄位：已填 {info['filled']}／{info['total']}"
             + ("（缺：" + "、".join(info["missing"]) + "）"
                if info["missing"] else "（全數齊備）"), "",
             "| 欄位 | 值 | 來源 |", "|---|---|---|"]
    mark = {"agent": "設計稿宣告", "context": "🤖 由 context.md 推導",
            "derived": "🤖 工具推導（請確認）", "missing": "⬅ 待填"}
    for row in etl_manifest.status_rows(manifest):
        lines.append(f"| {row['label']} | "
                     + (f"`{row['value']}`" if row["value"] else "（空）")
                     + f" | {mark.get(row['origin'], row['origin'])} |")
    if manifest["tables"]:
        lines += ["", "**逐表 ETL job**（每張表一個 job；沒覆寫就沿用 "
                  "pipeline 層預設）", "",
                  "| 表 | job id | 更新方式 | 更新頻率 | 來源 DB | 目標 DB "
                  "| CPU | Memory | owner |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for table in manifest["tables"]:
            cells = [f"`{table['table']}`"]
            for key in ("id", "write_mode", "schedule", "source_db",
                        "target_db", "cpu", "memory", "owner"):
                value = table["fields"][key]["value"]
                cells.append(f"`{value}`" if value else "⬅ 待填")
            lines.append("| " + " | ".join(cells) + " |")
    return lines


def _physical_md(name: str, round_no: int, result: dict,
                 gate_preview: dict | None, ddl_diff: str,
                 product: dict | None = None,
                 etl: dict | None = None) -> str:
    physical = result.get("physical_design") or {}
    tables = physical.get("tables") or []
    lines = [f"# 實體設計（Physical Design）— {name}（第 {round_no} 輪設計）", "",
             "> 🎨 design mode 產物：草稿 DDL 見同名 `"
             f"design_doc/{name}/{name}.design.sql`；定稿後由使用者存成 "
             f"`input/{name}/{name}.sql` 進入 govern mode。", ""]
    if str(physical.get("overview", "")).strip():
        lines += ["**實作策略**：" + str(physical["overview"]).strip(), ""]
    # 1. Entity Overview（總覽＋積木層級＋關鍵設計決策）
    lines += ["## 1. Entity Overview（實體總覽）", "",
              "| 表 | 積木層級 | Business Key | ENGINE | ORDER BY "
              "| PARTITION BY | 用途 | 關鍵設計決策 |",
              "|---|---|---|---|---|---|---|---|"]
    for table in tables:
        decisions = table.get("design_decisions") or []
        key_decision = decisions[0].get("decision", "") if decisions else ""
        if len(decisions) > 1:
            key_decision += f"（等 {len(decisions)} 項，見明細）"
        layer = LAYER_LABEL.get(table.get("layer"), table.get("layer") or "—")
        bk = "、".join(f"`{x}`" for x in
                       (table.get("keys") or {}).get("business_key") or [])
        lines.append(f"| `{table.get('name', '?')}` | {layer} "
                     f"| {bk or '—'} "
                     f"| `{table.get('engine', '')}` "
                     f"| `{table.get('order_by', '')}` "
                     f"| `{table.get('partition_by', '') or '—'}` "
                     f"| {str(table.get('comment', '')).strip()} "
                     f"| {key_decision} |")
    # 表間關係（Relations）——對 config 來源表的引用（自動衍生）＋
    # agent 宣告的設計內 FK；定稿時可直接沿用
    rels = all_relations(result)
    lines += ["", "### 表間關係（Relations）", ""]
    if rels:
        lines += ["| from（多的一方） | to（一的一方） | 基數 | 種類 | 說明 "
                  "| 來源 |",
                  "|---|---|---|---|---|---|"]
        lines += [f"| `{r.get('from', '')}` | `{r.get('to', '')}` "
                  f"| {r.get('cardinality', '')} | {r.get('kind', '')} "
                  f"| {r.get('note', '')} "
                  f"| {'🔗 自動衍生' if r.get('origin') == 'derived' else '宣告'} |"
                  for r in rels]
        lines += ["", f"（已同步輸出 relations 草稿：`design_doc/{name}/{name}"
                  ".design.relations.yaml`——含自動衍生的來源表引用，"
                  f"定稿時可直接沿用為 `input/{name}/relations.yaml`）"]
    else:
        lines.append("（未宣告且無外部 source——單表源生設計）")
    # 2. Entity Detail（規格＋欄位血緣＋逐表設計決策與理由）
    edges = downstream_edges(tables)
    lines += ["", "## 2. Entity Detail（實體明細）"]
    for table in tables:
        layer = LAYER_LABEL.get(table.get("layer"), table.get("layer") or "")
        lines += ["", f"### `{table.get('name', '?')}`"
                  + (f" — {layer}" if layer else ""),
                  str(table.get("comment", "")).strip(), "",
                  f"- ENGINE：`{table.get('engine', '')}`"
                  + (f" · ORDER BY `{table.get('order_by', '')}`"
                     if table.get("order_by") else "")
                  + (f" · PARTITION BY `{table.get('partition_by', '')}`"
                     if table.get("partition_by") else "")]
        cols = table.get("columns") or []
        if cols:
            lines += ["", "| 欄位 | 型別 | Nullable | 來源（從何處來） | COMMENT |",
                      "|---|---|---|---|---|"]
            lines += [f"| `{c.get('name', '')}` | `{c.get('type', '')}` "
                      f"| {'✅' if c.get('nullable') else ''} "
                      f"| {c.get('source', '') or '（本表源生）'} "
                      f"| {c.get('comment', '')} |" for c in cols]
        keys = table.get("keys") or {}
        lines += ["", "**Key 設計**", ""]
        bk = keys.get("business_key") or []
        lines.append("- **Business Key（一行的身分）**："
                     + ("、".join(f"`{x}`" for x in bk) if bk else "（未宣告）"))
        if table.get("order_by"):
            lines.append(f"- **排序鍵（ORDER BY）**：`{table['order_by']}`"
                         "——ClickHouse 排序鍵非唯一約束，唯一性語意見下")
        if str(keys.get("description", "")).strip():
            lines.append(f"- **Key 語意**：{str(keys['description']).strip()}")
        for jk in keys.get("join_keys") or []:
            lines.append(f"- **Join Key**：`{jk.get('column', '')}`"
                         + (f" → `{jk.get('references', '')}`"
                            if jk.get("references") else "")
                         + (f"（{jk.get('note', '')}）" if jk.get("note")
                            else ""))
        used_by = edges.get(str(table.get("name", ""))) or []
        lines += ["", "**欄位去向（去到何處——由各表 source 確定性反推）**", ""]
        lines += [f"- {edge}" for edge in used_by] or \
            ["（無下游設計表使用本表欄位）"]
        decisions = table.get("design_decisions") or []
        lines += ["", "**設計決策與理由**", ""]
        if decisions:
            lines += ["| 決策 | 理由 |", "|---|---|"]
            lines += [f"| {d.get('decision', '')} | {d.get('rationale', '')} |"
                      for d in decisions]
        else:
            lines.append("（未提供）")
    # 表名產品前綴檢查（context 宣告 product 時逐表檢查）
    prefix_rows = product_prefix_check(result, product)
    if prefix_rows:
        lines += ["", f"## 表名產品前綴檢查（產品：`{product['code']}`"
                  + (f"，{product.get('name', '')}" if product.get("name")
                     else "") + "）", ""]
        for r in prefix_rows:
            lines.append(f"- {'✅' if r['ok'] else '❌'} `{r['table']}`"
                         + ("" if r["ok"]
                            else f" — 應為 `{r['expected']}`"))
    # 跨表比對（多積木一致性——確定性檢查）
    xchecks = cross_table_checks(result)
    if xchecks:
        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
        lines += ["", "## 跨表比對（設計內多表一致性——確定性檢查）", ""]
        for x in xchecks:
            lines.append(f"- {icon.get(x['status'], '')} **{x['check']}**"
                         f"：{x['detail']}")
    lines += ["", "## 閘門預檢（以目前規則試跑草稿 DDL；設計參考、非正式判定）", ""]
    if not gate_preview:
        lines.append("（本輪未執行預檢）")
    elif gate_preview.get("parse_error"):
        lines.append(f"❌ 草稿 DDL 無法解析：{gate_preview['parse_error']}")
    else:
        flag = "✅ 預檢合規" if gate_preview.get("compliant") else "❌ 預檢不合規"
        lines.append(f"{flag} ｜ fail {gate_preview.get('fail', 0)}、"
                     f"warning {gate_preview.get('warning', 0)}")
        origins = gate_preview.get("origins") or {}

        def rule_line(icon: str, rule: str) -> str:
            origin = origins.get(rule)
            return (f"- {icon} `{rule}`"
                    + (f" — 依據：{_origin_md(origin)}" if origin else ""))

        if gate_preview.get("blocked"):
            lines.append("")
            lines.append("**卡下來的規則（點依據直達 config 規則檔）**")
            lines += [rule_line("❌", r) for r in gate_preview["blocked"]]
        if gate_preview.get("warned"):
            lines.append("")
            lines.append("**警告的規則**")
            lines += [rule_line("⚠️", r) for r in gate_preview["warned"]]
    lines += _etl_md(name, etl)
    notes = physical.get("notes") or []
    lines += ["", "## 設計注意事項", ""]
    lines += [f"- {n}" for n in notes] or ["（無）"]
    if ddl_diff:
        lines += ["", "## 與上一輪設計的 DDL 演進", "", "```diff", ddl_diff, "```"]
    return "\n".join(lines) + "\n"


def _story_md(name: str, round_no: int, result: dict,
              config_sources: list[tuple[str, str]] | None = None,
              required_sources: list[str] | None = None) -> str:
    """設計故事（給人讀的）：白話交代設計原因、取捨與實用指南，
    末尾自動彙整逐表決策速覽——工程師一份讀完就懂為什麼這樣設計。"""
    n = result.get("narrative") or {}
    lines = [f"# 設計故事 — {name}（第 {round_no} 輪設計）", "",
             f"> {str(n.get('tldr', '')).strip()}", "",
             "> 🎨 這份是**給人讀的設計說明**：為什麼這樣設計、取捨是什麼、"
             "怎麼用才對。", f"> 技術規格見 `{name}.logical_design.md`（邏輯）、"
             f"`{name}.physical_design.md`（實體）、`{name}.design.sql`（DDL）。",
             "", "## 為什麼需要這個主體", "",
             str(n.get("why", "")).strip(), ""]
    if str(n.get("how_design_thinks", "")).strip():
        lines += ["## 設計是怎麼想的", "",
                  str(n["how_design_thinks"]).strip(), ""]
    lines += ["## 關鍵取捨（選了什麼、放棄了什麼、為什麼）", ""]
    for tr in n.get("tradeoffs") or []:
        lines.append(f"- **選擇**：{tr.get('chose', '')}"
                     + (f" ｜ **而不是**：{tr.get('instead_of', '')}"
                        if tr.get("instead_of") else "")
                     + f"\n  - **因為**：{tr.get('because', '')}")
    lines += ["", "## 怎麼使用（實用指南）", ""]
    for u in n.get("how_to_use") or []:
        lines += [f"### {u.get('scenario', '')}", "",
                  str(u.get("guidance", "")).strip(), ""]
    pitfalls = n.get("pitfalls") or []
    if pitfalls:
        lines += ["## 常見誤用與陷阱", ""]
        lines += [f"- ⚠️ {p}" for p in pitfalls] + [""]
    lessons = n.get("lessons") or []
    if lessons:
        lines += ["## 給工程師的啟發（可複用的設計 pattern）", ""]
        lines += [f"- 💡 {x}" for x in lessons] + [""]
    # 設計出處：agent 宣告的想法來源 ＋ 工具紀錄的素材清單（兩層 provenance）
    lines += ["## 設計出處（這個設計從哪些 config 想法出發）", ""]
    refs = n.get("references") or []
    if refs:
        lines.append("**想法 → 來源（agent 宣告）**")
        lines += [f"- {_origin_md(str(r.get('source', '')))}："
                  f"{r.get('how', '')}" for r in refs]
        lines.append("")
    if config_sources:
        lines.append("**本輪設計餵入的 config 素材（工具紀錄，宣告 domain＋Common）**")
        lines += [f"- {kind}：{_origin_md(path)}"
                  for kind, path in config_sources]
        lines.append("")
    if not refs and not config_sources:
        lines += ["（本輪沒有可用的 config 參考素材——設計純依 context.md）", ""]
    # 必讀素材防漏：索引標必讀、卻沒出現在出處宣告 → 顯性提醒
    if required_sources:
        declared = {str(r.get("source", "")).strip().lower() for r in refs}
        missing = [p for p in required_sources if p.lower() not in declared]
        if missing:
            lines += ["> ⚠️ **必讀素材未見於出處宣告**："
                      + "、".join(f"`{p}`" for p in missing)
                      + "——請確認設計已對照這些素材；已參考的請補進 "
                      "narrative.references。", ""]
    # 決策速覽（自動彙整自 physical_design 的逐表 design_decisions）
    tables = (result.get("physical_design") or {}).get("tables") or []
    lines += ["## 決策速覽（自動彙整；完整規格見 physical_design.md）", ""]
    for t in tables:
        layer = LAYER_LABEL.get(t.get("layer"), t.get("layer") or "")
        lines.append(f"### `{t.get('name', '?')}`"
                     + (f" — {layer}" if layer else ""))
        for d in t.get("design_decisions") or []:
            lines.append(f"- **{d.get('decision', '')}**："
                         f"{d.get('rationale', '')}")
        lines.append("")
    return "\n".join(lines)


def design_sql_text(name: str, round_no: int, result: dict) -> str:
    """全量設計 DDL（各表合併，定稿入口）。逐表拆檔另見 design_ddl_files。"""
    tables = (result.get("physical_design") or {}).get("tables") or []
    split_note = ""
    if any(str(t.get("ddl", "")).strip() for t in tables):
        split_note = (f"-- 逐表拆檔（積木）見 design_doc/{name}/{name}.design/ "
                      f"資料夾（{len(tables)} 份 .ddl）\n")
    return (f"-- 第 {round_no} 輪設計 DDL — {name}（design mode 草稿，會隨迭代演進）\n"
            f"-- 邏輯／實體設計見 design_doc/{name}/{name}.logical_design.md、"
            f"{name}.physical_design.md\n" + split_note
            + f"-- 定稿後由使用者存成 input/{name}/{name}.sql（＋relations.yaml）"
            "進入 govern mode\n\n"
            + combined_ddl(result) + "\n")


def design_ddl_files(name: str, round_no: int, result: dict) -> dict[str, str]:
    """逐表 DDL 拆檔：{表名.ddl: 檔案內容}。表未附 ddl 時回空 dict（單檔模式）。"""
    out: dict[str, str] = {}
    for table in (result.get("physical_design") or {}).get("tables") or []:
        ddl = str(table.get("ddl", "")).strip()
        tname = str(table.get("name", "")).strip()
        if not ddl or not tname:
            continue
        layer = LAYER_LABEL.get(table.get("layer"), table.get("layer") or "")
        out[f"{tname}.ddl"] = (
            f"-- 第 {round_no} 輪設計 DDL — {name}/{tname}"
            + (f"（{layer}）" if layer else "") + "\n"
            f"-- 欄位來源與去向見 design_doc/{name}/{name}.physical_design.md；"
            f"全量合併版 design_doc/{name}/{name}.design.sql\n\n" + ddl + "\n")
    return out


_EXTERNAL_SRC_RE = re.compile(
    r"^([A-Za-z_]\w*)\.([A-Za-z_]\w*)\.([A-Za-z_]\w*)$")


def derived_source_relations(result: dict) -> list[dict]:
    """從欄位 source 自動衍生對 config 來源表的 relation。

    relation 的對象應該是 **config 的 source table（權威來源）**，而不是
    只在設計產出的表之間互指——欄位 source 為三段式 `DOMAIN.table.col`
    （外部權威）時，確定性衍生：
        from: <設計表>.<欄位>  to: DOMAIN.table.col  N:1 reference
    設計表之間的內部血緣（source＝本地表.欄位）屬積木組裝，不是 subject
    對外關係，不衍生。"""
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for t in (result.get("physical_design") or {}).get("tables") or []:
        if not isinstance(t, dict):
            continue
        for c in t.get("columns") or []:
            if not isinstance(c, dict):
                continue
            m = _EXTERNAL_SRC_RE.match(str(c.get("source", "")).strip())
            if not m:
                continue
            src = f"{t.get('name', '')}.{c.get('name', '')}"
            dst = m.group(0)
            key = (src.lower(), dst.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append({"from": src, "to": dst, "cardinality": "N:1",
                        "kind": "reference",
                        "note": "自動衍生自欄位 source（config 來源表）",
                        "origin": "derived"})
    return out


def all_relations(result: dict) -> list[dict]:
    """subject 的完整關係＝agent 宣告的 table_relations ＋ 自動衍生的
    source 引用（去重：宣告過的不重複衍生）。每項帶 origin
    （declared｜derived）。"""
    declared = []
    seen: set[tuple[str, str]] = set()
    for r in (result.get("physical_design") or {}).get("table_relations") or []:
        if not isinstance(r, dict):
            continue
        key = (str(r.get("from", "")).lower(), str(r.get("to", "")).lower())
        seen.add(key)
        declared.append({**r, "origin": "declared"})
    derived = [r for r in derived_source_relations(result)
               if (r["from"].lower(), r["to"].lower()) not in seen]
    return declared + derived


def design_relations_yaml(name: str, round_no: int,
                          result: dict) -> str | None:
    """關係 → relations 草稿（格式同 input/<名>/relations.yaml）：
    agent 宣告＋自動衍生（來源表引用）合併輸出。"""
    rels = all_relations(result)
    if not rels:
        return None
    entries = []
    for r in rels:
        entry = {"from": str(r.get("from", "")), "to": str(r.get("to", ""))}
        if r.get("cardinality"):
            entry["cardinality"] = str(r["cardinality"])
        if r.get("kind"):
            entry["kind"] = str(r["kind"])
        if r.get("note"):
            entry["note"] = str(r["note"])
        entries.append(entry)
    header = (f"# 第 {round_no} 輪設計的 relations 草稿 — {name}"
              "（design mode 產物）。\n"
              "# 含自動衍生：欄位 source 指向外部權威（DOMAIN.table.col）者，\n"
              "# 對 config 來源表的引用關係已確定性衍生，不必手填。\n"
              f"# 定稿時由使用者存成 input/{name}/relations.yaml。\n")
    return header + yaml.safe_dump({"relations": entries}, allow_unicode=True,
                                   sort_keys=False)


def render(name: str, result: dict, context_text: str, history_root: str,
           report_dir: str, gate_preview: dict | None = None,
           answers: dict | None = None,
           config_sources: list[tuple[str, str]] | None = None,
           product: dict | None = None,
           required_sources: list[str] | None = None,
           etl: dict | None = None) -> dict:
    """輪次追蹤＋渲染設計產物。回傳 track_round 的資訊＋檔案路徑。

    `etl`＝`etl_manifest.build()` 的結果；沒帶時就地從 context 組一份，
    確保 design mode 一定會產出 ETL 建議檔（沒資訊也長殼）。"""
    info = track_round(history_root, name, context_text, result)
    round_no = info["round"]
    if etl is None:
        meta, _ = parse_context(context_text)
        etl = etl_manifest.build(name, result, meta)
    outputs = {
        f"{name}.design_story.md": _story_md(
            name, round_no, result, config_sources=config_sources,
            required_sources=required_sources),
        f"{name}.logical_design.md": _logical_md(name, round_no, result,
                                                 answers=answers),
        f"{name}.physical_design.md": _physical_md(
            name, round_no, result, gate_preview, info.get("ddl_diff", ""),
            product=product, etl=etl),
        f"{name}.design.sql": design_sql_text(name, round_no, result),
        f"{name}.etl.yaml": etl_manifest.to_yaml(name, round_no, etl),
    }
    os.makedirs(report_dir, exist_ok=True)
    for fname, text in outputs.items():
        _write_if_changed(os.path.join(report_dir, fname), text)
    # relations 草稿（有表間關係才產；沒有時清掉舊檔避免誤導）
    rel_path = os.path.join(report_dir, f"{name}.design.relations.yaml")
    rel_text = design_relations_yaml(name, round_no, result)
    if rel_text:
        _write_if_changed(rel_path, rel_text)
        outputs[f"{name}.design.relations.yaml"] = rel_text
    elif os.path.isfile(rel_path):
        os.remove(rel_path)
    # 逐表 DDL 拆檔（積木）→ design_doc/<名>/<名>.design/；本輪不存在的表清掉
    ddl_files = design_ddl_files(name, round_no, result)
    ddl_dir = os.path.join(report_dir, f"{name}.design")
    if ddl_files:
        os.makedirs(ddl_dir, exist_ok=True)
        for fname, text in ddl_files.items():
            _write_if_changed(os.path.join(ddl_dir, fname), text)
        for fn in sorted(os.listdir(ddl_dir)):
            if fn.endswith(".ddl") and fn not in ddl_files:
                os.remove(os.path.join(ddl_dir, fn))
    info["ddl_files"] = len(ddl_files)
    info["files"] = sorted(outputs)
    return info
