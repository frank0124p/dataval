"""正式區資產（production assets）——已核准 data subject 的三件輸入。

`production/<域>/<subject>/` 裡的 `<subject>.sql`／`.relations.yaml`／
`.context.md` 是**已經核准上線**的資產。它們理應是所有新設計的第一手素材：
新表要組之前，先問「這件事是不是已經有人做過了」。

這個模組讓正式區在兩個模式都被看見：

  1. **每次起跑掃一遍**，把資產清單寫成 `config/Common/production/registry.md`
     （自動生成、內容確定性）。放在 **Common** ⇒ 不論宣告哪個 domain 都載入，
     且在設計素材索引裡標成**必讀**——agent 起草前一定會讀到。
  2. **沒複用就顯性提醒**：新 subject 完全沒有引用任何正式區資產時，
     govern 出閘門 `PRODUCTION.REUSE` 警告（不擋合規），design 在報告提醒；
     兩邊都確定性產生一題問答，請使用者交代「為什麼不複用」。

判定「有複用」只看確定性證據，不猜：
  - `relations.yaml` 的三段式端點 `DOMAIN.table.col` 指到正式區的表
  - 設計稿欄位 `source` 的三段式 `DOMAIN.table.col` 指到正式區的表

零 LLM、純函式；正式區是空的就完全不作用（新專案不該被這條煩）。
"""
from __future__ import annotations

import os
import re

from .model import Finding, ZONE_GATING
from .parser import parse_ddl
from .precheck import parse_context

#: 自動生成的資產索引（放 Common → 所有 domain 都吃得到）
REGISTRY_REL = "Common/production/registry.md"
RULE_ID = "PRODUCTION.REUSE"

_TRIPLE = re.compile(r"^([A-Za-z_]\w*)\.([A-Za-z_]\w*)\.([A-Za-z_]\w*)$")

#: 稽核欄到處都同名，當候選只是雜訊（與設計期 X4 重複承載檢查同一組排除）
_AUDIT_COLUMNS = {"created_at", "updated_at", "deleted_at", "id"}
#: 候選最多列這麼多列（prompt 要保持精簡；超出只留最有線索的）
CANDIDATE_LIMIT = 30


def _first_paragraph(text: str) -> str:
    """context.md 的第一段實質敘述（給索引當一句話摘要）。"""
    # parse_context 回傳 (front-matter, {段落標題: 內容})——取第一段有內容的
    _, sections = parse_context(text)
    body = "\n".join(sections.values())
    for raw in body.splitlines():
        line = " ".join(raw.split())
        if line and not line.startswith(("#", "|", ">", "-", "```")):
            return line[:80] + ("…" if len(line) > 80 else "")
    return ""


def scan(production_root: str, dialect: str = "clickhouse") -> list[dict]:
    """掃正式區。回傳 [{domain, subject, tables, purpose, files}]，排序固定。"""
    out: list[dict] = []
    if not production_root or not os.path.isdir(production_root):
        return out
    for domain in sorted(os.listdir(production_root)):
        dom_path = os.path.join(production_root, domain)
        if not os.path.isdir(dom_path) or domain.startswith("_"):
            continue
        for subject in sorted(os.listdir(dom_path)):
            sub_path = os.path.join(dom_path, subject)
            if not os.path.isdir(sub_path):
                continue
            files = {}
            for key, suffix in (("sql", ".sql"), ("relations", ".relations.yaml"),
                                ("context", ".context.md")):
                path = os.path.join(sub_path, subject + suffix)
                if os.path.isfile(path):
                    files[key] = f"production/{domain}/{subject}/{subject}{suffix}"
            tables: list[str] = []
            columns: dict[str, list[dict]] = {}
            if "sql" in files:
                try:
                    with open(os.path.join(sub_path, subject + ".sql"),
                              encoding="utf-8") as f:
                        parsed = parse_ddl(f.read(), dialect=dialect).tables
                    tables = [t.name for t in parsed]
                    columns = {t.name: [{"name": c.name, "type": c.base_type,
                                         "comment": c.comment or ""}
                                        for c in t.columns] for t in parsed}
                except Exception:
                    tables, columns = [], {}
            purpose = ""
            if "context" in files:
                try:
                    with open(os.path.join(sub_path, subject + ".context.md"),
                              encoding="utf-8") as f:
                        purpose = _first_paragraph(f.read())
                except Exception:
                    purpose = ""
            out.append({"domain": domain, "subject": subject,
                        "tables": tables, "columns": columns,
                        "purpose": purpose, "files": files})
    return out


def table_index(assets: list[dict]) -> dict[str, dict]:
    """`domain.table`（小寫）→ 資產。判定複用時用這張表比對。"""
    return {f"{a['domain']}.{t}".lower(): a
            for a in assets for t in a["tables"]}


# ---------------------------------------------------------------- 索引檔

def registry_md(assets: list[dict]) -> str:
    """資產索引全文（確定性）。front-matter 讓它在設計素材索引裡標成必讀。"""
    total_tables = sum(len(a["tables"]) for a in assets)
    summary = (f"正式區已核准 {len(assets)} 個 data subject、{total_tables} 張表"
               "——設計新表前先讀，能複用就不要重造"
               if assets else "正式區目前是空的（尚無已核准的 data subject）")
    lines = [
        "---",
        f"index_summary: {summary}",
        "index_stage: [L, P]",
        "index_required: true",
        "---",
        "",
        "# 正式區資產（production assets）",
        "",
        "> 🤖 **自動生成，勿手改**：每次 `run.py` 起跑時依 `production/` 重新產生。",
        "> 這裡列的是**已核准上線**的 data subject——設計新表前先看這份，",
        "> 同一件事已經有人做過就直接引用，不要在自己的主體裡重造一份。",
        "",
    ]
    if not assets:
        lines += ["（正式區目前是空的。等第一個 subject 晉升後，這裡會自動列出。）",
                  ""]
        return "\n".join(lines)
    lines += ["| Domain | Subject | 表 | 用途 |", "|---|---|---|---|"]
    for a in assets:
        tables = "、".join(f"`{t}`" for t in a["tables"]) or "（DDL 解析不到表）"
        lines.append(f"| `{a['domain']}` | `{a['subject']}` | {tables} "
                     f"| {a['purpose'] or '（context 未提供摘要）'} |")
    lines += ["", "## 每個資產的三件輸入（要看細節就開這些檔）", ""]
    for a in assets:
        lines.append(f"### `{a['domain']}.{a['subject']}`")
        for key, label in (("sql", "DDL"), ("relations", "表間關聯"),
                           ("context", "語意描述")):
            path = a["files"].get(key)
            lines.append(f"- {label}：" + (f"`{path}`" if path else "（缺）"))
        lines.append("")
    lines += [
        "## 怎麼引用（確定性寫法）",
        "",
        "- `relations.yaml`：`to: <DOMAIN>.<表>.<欄>`（三段式）",
        "- 設計稿欄位：`source: <DOMAIN>.<表>.<欄>`——工具會自動衍生對來源表的",
        "  reference 關係，不必手填 table_relations",
        "- **引用只存鍵**：外部權威的屬性（名稱、等級…）不要複製進自己的表",
        "",
    ]
    return "\n".join(lines)


def write_registry(config_dir: str, assets: list[dict]) -> tuple[str, bool]:
    """寫入 config/Common/production/registry.md；內容沒變不改寫。"""
    path = os.path.join(config_dir, *REGISTRY_REL.split("/"))
    text = registry_md(assets)
    old = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old == text:
        return path, False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, True


# ---------------------------------------------------------------- 複用判定

def _referenced_from_triples(triples, index: dict[str, dict]) -> list[str]:
    hit: list[str] = []
    for raw in triples:
        m = _TRIPLE.match(str(raw or "").strip())
        if not m:
            continue
        key = f"{m.group(1)}.{m.group(2)}".lower()
        if key in index and key not in hit:
            hit.append(key)
    return sorted(hit)


def referenced_by_relations(relations, assets: list[dict]) -> list[str]:
    """relations.yaml 引用到的正式區表（`DOMAIN.table` 小寫）。"""
    index = table_index(assets)
    triples = []
    for rel in relations or []:
        if isinstance(rel, dict):
            triples += [rel.get("to"), rel.get("from")]
    return _referenced_from_triples(triples, index)


def referenced_by_design(result: dict, assets: list[dict]) -> list[str]:
    """設計稿（欄位 source ＋ table_relations）引用到的正式區表。"""
    index = table_index(assets)
    triples = []
    physical = (result or {}).get("physical_design") or {}
    for table in physical.get("tables") or []:
        if not isinstance(table, dict):
            continue
        for column in table.get("columns") or []:
            if isinstance(column, dict):
                triples.append(column.get("source"))
    for rel in physical.get("table_relations") or []:
        if isinstance(rel, dict):
            triples += [rel.get("to"), rel.get("from")]
    return _referenced_from_triples(triples, index)


def _asset_summary(assets: list[dict], limit: int = 6) -> str:
    names = [f"{a['domain']}.{a['subject']}" for a in assets]
    return "、".join(f"`{n}`" for n in names[:limit]) + \
        ("…" if len(names) > limit else "")


# ------------------------------------------------ 語意建議的素材與候選

def candidates(pairs, assets: list[dict],
               referenced: list[str] | None = None) -> list[dict]:
    """**確定性**的疑似複用候選：本主體的欄位與正式區某張表的欄位同名，
    但還沒宣告引用關係。這不是判定，只是把「值得語意判讀的點」挑出來
    餵給顧問區——真正該不該引用要看語意（同名不一定同義）。

    pairs＝[(表名, 欄名)]；referenced＝已經引用的 `domain.table`（會排除）。
    回傳 [{local, production, column, purpose, why}]，排序固定。"""
    done = set(referenced or [])
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for table_name, column in pairs:
        col = str(column or "").strip().lower()
        if not col or col in _AUDIT_COLUMNS:
            continue      # 稽核欄同名是常態，不是複用線索
        for asset in assets:
            key = f"{asset['domain']}.{asset['subject']}".lower()
            for prod_table, cols in (asset.get("columns") or {}).items():
                if f"{asset['domain']}.{prod_table}".lower() in done:
                    continue
                match = next((c for c in cols
                              if c["name"].lower() == col), None)
                if not match:
                    continue
                pair_key = (f"{table_name}.{col}".lower(),
                            f"{asset['domain']}.{prod_table}.{col}".lower())
                if pair_key in seen:
                    continue
                seen.add(pair_key)
                out.append({
                    "local": f"{table_name}.{column}",
                    "production": f"{asset['domain']}.{prod_table}.{match['name']}",
                    "subject": key,
                    "purpose": asset.get("purpose", ""),
                    "why": ("同名 join key" if col.endswith("_id")
                            else "同名欄位"),
                })
    # join key（_id）排前面——那是最可能真的該引用的線索
    out.sort(key=lambda x: (0 if x["why"] == "同名 join key" else 1,
                            x["local"].lower(), x["production"].lower()))
    return out[:CANDIDATE_LIMIT]


def schema_pairs(schema) -> list[tuple[str, str]]:
    """Schema → [(表名, 欄名)]（候選比對用）。"""
    return [(t.name, c.name) for t in getattr(schema, "tables", []) or []
            for c in t.columns]


def design_pairs(result: dict) -> list[tuple[str, str]]:
    """設計稿 → [(表名, 欄名)]。"""
    out = []
    for table in ((result or {}).get("physical_design") or {}).get("tables") or []:
        if not isinstance(table, dict):
            continue
        for column in table.get("columns") or []:
            if isinstance(column, dict) and column.get("name"):
                out.append((str(table.get("name", "")), str(column["name"])))
    return out


def advisory_material(assets: list[dict], hits: list[dict],
                      referenced: list[str] | None = None) -> str:
    """顧問區 prompt 的「正式區資產」區塊：可複用的資產清單＋確定性候選。
    語意判讀由 agent 做，這裡只提供素材與線索。"""
    if not assets:
        return "（正式區目前是空的——沒有可複用的已核准主體）"
    lines = ["**已核准上線的主體（可直接引用，不要重造）**", ""]
    for asset in assets:
        for table in asset["tables"]:
            cols = ", ".join(c["name"] for c in
                             (asset.get("columns") or {}).get(table, []))
            lines.append(f"- `{asset['domain']}.{table}`"
                         f"（{asset['domain']}.{asset['subject']}）"
                         + (f"：{asset['purpose']}" if asset["purpose"] else "")
                         + (f"\n  - 欄位：{cols}" if cols else ""))
    lines.append("")
    if referenced:
        lines.append("**本主體已宣告引用**："
                     + "、".join(f"`{r}`" for r in referenced))
        lines.append("")
    lines += ["**確定性候選（同名欄位；同名不一定同義——請語意判讀）**", ""]
    if hits:
        lines += ["| 本主體欄位 | 正式區欄位 | 線索 |", "|---|---|---|"]
        lines += [f"| `{h['local']}` | `{h['production']}` | {h['why']} |"
                  for h in hits]
        if len(hits) >= CANDIDATE_LIMIT:
            lines += ["", f"（候選只列前 {CANDIDATE_LIMIT} 筆，"
                      "其餘同性質的請一併判讀）"]
    else:
        lines.append("（沒有同名欄位——請改從**語意**判讀：本主體要承載的事實"
                     "是否已由上面某個主體承載，即使欄名不同）")
    return "\n".join(lines)


# ---------------------------------------------------------------- 閘門檢查

def run(schema, relations, production_root: str,
        dialect: str = "clickhouse") -> list[Finding]:
    """閘門區確定性檢查（警告，不擋）：新 subject 有沒有複用正式區資產。

    正式區是空的 → 不產生任何 finding（新專案不該被這條煩）。"""
    assets = scan(production_root, dialect)
    if not assets:
        return []
    hit = referenced_by_relations(relations, assets)
    if hit:
        return [Finding(
            RULE_ID, "ssot", "pass", "(schema)",
            f"已引用正式區資產：{'、'.join(f'`{h}`' for h in hit)}。",
            rationale="複用已核准資產可避免同一事實出現第二份權威。",
            expected="新 subject 引用正式區的既有資產", actual="已引用",
            severity="info", source="rule", zone=ZONE_GATING)]
    return [Finding(
        RULE_ID, "ssot", "warning", "(schema)",
        f"沒有引用任何正式區資產（正式區現有 {len(assets)} 個已核准主體："
        f"{_asset_summary(assets)}）。組新表前請先確認這些主體是否已承載"
        "你要的事實——能引用就引用，不要在本主體重造一份。",
        rationale="正式區是已核准的權威；不複用而各自重造，同一事實會出現"
                  "多份來源，跨域分析對不起來。",
        expected="relations.yaml 以三段式 `DOMAIN.table.col` 引用正式區資產，"
                 "或明確交代為何本主體無上游",
        actual="relations.yaml 沒有任何指向正式區的三段式端點",
        fix="檢視 config/Common/production/registry.md，把該引用的關係補進 "
            "relations.yaml；確實無上游時在 answers.yaml 交代原因",
        severity="warning", source="rule", zone=ZONE_GATING)]


# ---------------------------------------------------------------- 問答題

def open_question(subject: str, assets: list[dict],
                  referenced: list[str]) -> dict | None:
    """沒複用時的問答題（確定性、附代填答案）。有複用就回 None。"""
    if not assets or referenced:
        return None
    return {
        "id": f"{RULE_ID}@{subject}",
        "question": f"【正式區複用】{subject} 目前沒有引用任何正式區資產"
                    f"（現有 {_asset_summary(assets)}）——是這些主體都沒有你要的"
                    "事實，還是漏了該建立的引用？",
        "answer": "（請擇一交代）① 確實無上游：本主體是源頭資料，"
                  "正式區沒有可複用的既有事實；② 漏了引用：請補進 "
                  "relations.yaml 的三段式端點後改為 structural 並重跑。",
        "kind": "semantic",
        "status": "proposed",
    }
