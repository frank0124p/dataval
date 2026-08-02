"""Minimal Mermaid ER diagram parser used as lineage evidence.

ER relationships describe structural associations, not observed data flow.
The parser therefore returns evidence only; lineage.py decides whether a safe
direction can be suggested from Business Keys and shared identifier columns.

標準撰寫格式是 Markdown（```mermaid fence 內放圖，fence 外可寫說明文字）；
`extract_mermaid` 負責取出 fence 內容。舊式純 .mmd 檔仍相容。
`config/<域>/erd/tables/*.md` 是參考表用途描述（檔名＝表名），
input 新產生的表會對照這些 reference 驗證是否正確引用。
"""
from __future__ import annotations

import os
import re
from . import config_dirs

_MERMAID_FENCE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


def extract_mermaid(text: str) -> str:
    """取出 Markdown 中所有 ```mermaid fence 的內容（多個 fence 合併）。
    沒有 fence 時原文返回——讓純 mermaid 內容（.mmd 風格）也能直接解析。"""
    blocks = _MERMAID_FENCE.findall(text)
    if blocks:
        return "\n".join(block.strip("\n") for block in blocks)
    return text


def entity_reference_findings(schema, er_diagram: dict | None) -> list:
    """ER 參考模型 entity 欄位定義 → input DDL 的確定性對照。

    參考模型（config/<域>/erd/*.md 或個案 ER 圖）的 entity 若定義了欄位，
    本次 DDL 的同名表逐欄比對：
      - 參考模型定義的欄位缺漏 → 閘門警告（不擋）
      - 參考模型標 PK 的欄位未列入 PRIMARY KEY／business key → 閘門警告
      - 全數存在 → pass
    與 production 基準互補：production 是「已核准的實體」，ER 參考模型是
    「設計期的應然」。完全確定性、零 LLM。"""
    from .model import Finding, ZONE_GATING
    out: list = []
    if not er_diagram:
        return out
    entities = er_diagram.get("entities") or {}
    by_lower = {name.lower(): ent for name, ent in entities.items()}
    for table in schema.tables:
        ent = by_lower.get(table.name.lower())
        columns = (ent or {}).get("columns") or []
        if not columns:
            continue
        src = ent.get("source") or er_diagram.get("source") or "config/<域>/erd"
        table_cols = {c.name.lower() for c in table.columns}
        missing = [c["name"] for c in columns
                   if c["name"].lower() not in table_cols]
        if missing:
            out.append(Finding(
                "ERD.ENTITY_REFERENCE", "structural", "warning", table.name,
                f"參考模型定義的欄位在本次 DDL 缺漏：{missing}。",
                severity="warning", source="rule", zone=ZONE_GATING,
                expected="參考模型 entity 欄位齊備："
                         f"{[c['name'] for c in columns]}",
                actual=f"缺 {missing}",
                fix="補上欄位，或更新參考模型使其反映現況",
                rationale=f"依據：{src}"))
        else:
            out.append(Finding(
                "ERD.ENTITY_REFERENCE", "structural", "pass", table.name,
                f"參考模型 entity 欄位對照：{len(columns)} 欄全數存在。",
                severity="info", source="rule", zone=ZONE_GATING,
                rationale=f"依據：{src}"))
        keys = set(table.primary_key) | set(table.business_key)
        pk_missing = [c["name"] for c in columns
                      if "PK" in (c.get("flags") or [])
                      and c["name"].lower() in table_cols
                      and c["name"] not in keys]
        if pk_missing:
            out.append(Finding(
                "ERD.ENTITY_REFERENCE", "structural", "warning", table.name,
                f"參考模型標 PK 的欄位未列入 PRIMARY KEY／business key："
                f"{pk_missing}。",
                severity="warning", source="rule", zone=ZONE_GATING,
                expected=f"{pk_missing} 為表的識別鍵",
                actual="欄位存在但未宣告為鍵",
                fix="於 DDL 宣告 PRIMARY KEY 或在 context.md 補 business_keys",
                rationale=f"依據：{src}"))
    return out


def load_table_purposes(config_dir: str, domains: list[str] | None,
                        problems: list[str] | None = None) -> dict:
    """載入參考表用途描述：config/<域>/erd/tables/<表名>.md。

    回傳 {表名: {"purpose": 描述, "source": "<域>/erd/tables/<檔>"}}。
    Common 先載入，宣告的域後載入（同名表以域的描述覆蓋）。
    描述取檔案全文（去掉開頭的 # 標題行）；壞檔記 problem、不擋。"""
    out: dict[str, dict] = {}
    for folder, dpath in config_dirs.domain_folders(config_dir, domains):
        tables_dir = os.path.join(dpath, "erd", "tables")
        if not os.path.isdir(tables_dir):
            continue
        for fn in sorted(os.listdir(tables_dir)):
            if not fn.endswith(".md") or fn.lower().startswith("readme"):
                continue
            label = f"{folder}/erd/tables/{fn}"
            try:
                with open(os.path.join(tables_dir, fn), encoding="utf-8") as f:
                    text = f.read().strip()
            except Exception as error:
                if problems is not None:
                    problems.append(f"{label}：{type(error).__name__}: {error}")
                continue
            lines = text.splitlines()
            if lines and lines[0].lstrip().startswith("#"):
                lines = lines[1:]
            purpose = "\n".join(lines).strip()
            if not purpose:
                if problems is not None:
                    problems.append(f"{label}：內容是空的（已略過）")
                continue
            out[os.path.splitext(fn)[0]] = {"purpose": purpose, "source": label}
    return out


_ENTITY = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*$")
_COLUMN = re.compile(r"^\s*(\S+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*?)\s*$")
_RELATION = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"([|o}{]+)--([|o}{]+)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$")


def parse_mermaid(text: str, source: str = "") -> dict:
    """Parse the common ``erDiagram`` subset without external dependencies."""
    entities: dict[str, dict] = {}
    relationships: list[dict] = []
    errors: list[str] = []
    current: str | None = None
    saw_header = False

    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        if line in ("```mermaid", "```"):
            continue
        if line == "erDiagram":
            saw_header = True
            continue
        if current:
            if line == "}":
                current = None
                continue
            match = _COLUMN.match(raw)
            if not match:
                errors.append(f"第 {line_number} 行無法解析 entity 欄位：{line}")
                continue
            raw_type, name, rest = match.groups()
            flags = [flag for flag in ("PK", "FK", "UK")
                     if re.search(rf"\b{flag}\b", rest, re.IGNORECASE)]
            entities[current]["columns"].append({
                "name": name,
                "type": raw_type,
                "flags": flags,
            })
            continue

        entity = _ENTITY.match(raw)
        if entity:
            current = entity.group(1)
            entities.setdefault(current, {"name": current, "columns": []})
            continue
        relation = _RELATION.match(raw)
        if relation:
            left, left_cardinality, right_cardinality, right, label = relation.groups()
            relationships.append({
                "left": left,
                "right": right,
                "left_cardinality": left_cardinality,
                "right_cardinality": right_cardinality,
                "label": label,
            })
            entities.setdefault(left, {"name": left, "columns": []})
            entities.setdefault(right, {"name": right, "columns": []})
            continue
        errors.append(f"第 {line_number} 行無法解析：{line}")

    if current:
        errors.append(f"entity '{current}' 缺少結尾 }}")
    if not saw_header:
        errors.append("缺少 erDiagram 標頭")
    return {
        "source": source,
        "entities": entities,
        "relationships": relationships,
        "errors": errors,
    }
