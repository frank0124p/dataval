"""建議 DDL 組建（proposal）：從 config 參考模型自動推導對照基準。

依 context.md 宣告的域，讀取 config/<域>/erd 的完整參考模型
（entity 欄位定義＋關係＋erd/tables 用途），以本次 input 的表為錨點：

  1. 取參考模型中與錨點連通的 entity 子圖
  2. 組出建議 Join SQL（join 鍵由 PK 標記／共同欄位推導；推不出時留 TODO）
  3. 產生「未來會使用的 DDL」——裝這段 SQL 結果的寬表（建議值）
  4. 與 input DDL 逐欄對比：建議欄位在 input 的落點／input 獨有欄位

完全確定性（純 config 推導、零 LLM）；產物一律**建議值**：
顧問區 info（PROPOSAL.DDL），永不影響合規判定。每輪隨 input／答案
演進重新組建，由 iterations/ 記錄（round_<N>.proposal.md）。
"""
from __future__ import annotations

import os

from .er_diagram import extract_mermaid, parse_mermaid


# ---------------------------------------------------------------- 參考模型載入

def load_domain_er_full(config_dir: str, domains: list[str] | None,
                        ) -> dict:
    """載入 Common＋宣告域的完整 ER 參考模型（不過濾、含 entity 欄位）。"""
    merged = {"entities": {}, "relationships": []}
    root = config_dir
    if os.path.isdir(os.path.join(config_dir, "domains")):
        root = os.path.join(config_dir, "domains")
    if not os.path.isdir(root):
        return merged
    folders = {f.lower(): f for f in os.listdir(root)
               if os.path.isdir(os.path.join(root, f)) and not f.startswith("_")}
    seen: set[str] = set()
    seen_rel: set[tuple] = set()
    for want in ["Common"] + [d for d in (domains or []) if d]:
        folder = folders.get(want.strip().lower())
        if not folder or folder in seen:
            continue
        seen.add(folder)
        erd_dir = os.path.join(root, folder, "erd")
        if not os.path.isdir(erd_dir):
            continue
        for fn in sorted(os.listdir(erd_dir)):
            if not fn.endswith((".md", ".mmd", ".mermaid")):
                continue
            if fn.lower().startswith("readme"):
                continue
            path = os.path.join(erd_dir, fn)
            if os.path.isdir(path):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            if fn.endswith(".md"):
                text = extract_mermaid(text)
            parsed = parse_mermaid(text, source=f"{folder}/erd/{fn}")
            for name, ent in (parsed.get("entities") or {}).items():
                target = merged["entities"].setdefault(
                    name, {"name": name, "columns": [], "source": ""})
                if ent.get("columns") and not target["columns"]:
                    target["columns"] = list(ent["columns"])
                    target["source"] = f"{folder}/erd/{fn}"
            for rel in parsed.get("relationships") or []:
                key = (rel.get("left"), rel.get("right"), rel.get("label"))
                if key not in seen_rel:
                    seen_rel.add(key)
                    merged["relationships"].append(rel)
    return merged


# ---------------------------------------------------------------- 組建

def _pk_columns(entity: dict) -> list[str]:
    return [c["name"] for c in entity.get("columns") or []
            if "PK" in (c.get("flags") or [])]


def _column_names(entity: dict) -> set[str]:
    return {c["name"] for c in entity.get("columns") or []}


def _join_condition(left: dict, right: dict, label: str) -> str:
    """推導 join 鍵：右表 PK 出現在左表 → 用它；否則共同 *_id 欄位；
    再推不出就留 TODO（帶關係語意），不硬猜。"""
    for pk in sorted(_pk_columns(right)):
        if pk in _column_names(left):
            return f"{left['name']}.{pk} = {right['name']}.{pk}"
    for pk in sorted(_pk_columns(left)):
        if pk in _column_names(right):
            return f"{left['name']}.{pk} = {right['name']}.{pk}"
    shared = sorted(c for c in _column_names(left) & _column_names(right)
                    if c.endswith("_id"))
    if shared:
        return f"{left['name']}.{shared[0]} = {right['name']}.{shared[0]}"
    return (f"1 = 1 /* TODO: 依關係「{label or '未命名'}」補 join 鍵"
            f"（參考模型未定義可推導的鍵欄位） */")


def build(schema, config_dir: str, domains: list[str] | None,
          purposes: dict | None = None) -> dict | None:
    """組建建議 Join SQL＋未來 DDL＋與 input 的逐欄對比。

    錨點＝input 表 ∩ 參考模型 entity；無錨點或無關係可組時回 None。"""
    er = load_domain_er_full(config_dir, domains)
    entities = er["entities"]
    if not entities:
        return None
    input_tables = {t.name.lower(): t for t in schema.tables}
    by_lower = {n.lower(): n for n in entities}
    anchors = sorted(by_lower[low] for low in by_lower if low in input_tables)
    if not anchors:
        return None

    # 錨點所在的連通子圖（沿參考模型關係擴張——含 input 尚未涵蓋的表）
    adjacency: dict[str, list[tuple[str, str, dict]]] = {}
    for rel in er["relationships"]:
        left, right = str(rel.get("left")), str(rel.get("right"))
        label = str(rel.get("label") or "")
        adjacency.setdefault(left, []).append((right, label, rel))
        adjacency.setdefault(right, []).append((left, label, rel))
    for edges in adjacency.values():
        edges.sort(key=lambda e: (e[0], e[1]))   # 確定性走訪順序
    component: set[str] = set()
    queue = list(anchors)
    while queue:
        node = queue.pop(0)
        if node in component:
            continue
        component.add(node)
        for neighbor, _, _ in adjacency.get(node, []):
            if neighbor not in component:
                queue.append(neighbor)

    # 基底表：關係數最多的錨點（平手取名稱序）
    base = max(anchors,
               key=lambda n: (len(adjacency.get(n, [])), ), default=anchors[0])
    base = sorted([a for a in anchors
                   if len(adjacency.get(a, [])) ==
                   len(adjacency.get(base, []))])[0]

    # BFS join 順序（確定性）：base 出發沿關係展開。
    # 基數註記：ER 記號兩端皆「多」（含 { 或 }）＝ N:M → 警示需中介表。
    def _is_many(token) -> bool:
        return "{" in str(token or "") or "}" in str(token or "")

    join_order: list[str] = [base]
    joins: list[dict] = []
    warnings: list[str] = []
    visited = {base}
    queue = [base]
    while queue:
        node = queue.pop(0)
        for neighbor, label, rel in adjacency.get(node, []):
            if neighbor in visited or neighbor not in component:
                continue
            visited.add(neighbor)
            join_order.append(neighbor)
            condition = _join_condition(entities[node], entities[neighbor],
                                        label)
            both_many = (_is_many(rel.get("left_cardinality")) and
                         _is_many(rel.get("right_cardinality")))
            if both_many:
                condition += " /* ⚠️ N:M 關係——直接 join 會展開重複列，建議中介表 */"
                warnings.append(
                    f"{rel.get('left')} ↔ {rel.get('right')} 為 N:M 關係"
                    f"（{label or '未命名'}）：寬表直接 join 會產生重複列，"
                    "建議建立中介（bridge）表或改以聚合處理。")
            joins.append({
                "table": neighbor, "via": node, "label": label,
                "condition": condition, "nm": both_many,
            })
            queue.append(neighbor)

    # SELECT 欄位與寬表 DDL 欄位（名稱衝突以表前綴消歧）
    select_cols: list[str] = []
    ddl_cols: list[dict] = []
    seen_cols: set[str] = set()
    for name in join_order:
        entity = entities[name]
        columns = entity.get("columns") or []
        if not columns:
            select_cols.append(f"  /* {name}.* —— 參考模型未定義欄位，"
                               "請於 config erd 補上 entity 欄位 */")
            continue
        for c in columns:
            out_name = c["name"]
            if out_name in seen_cols:
                out_name = f"{name}_{c['name']}"
                select_cols.append(f"  {name}.{c['name']} AS {out_name},")
            else:
                select_cols.append(f"  {name}.{c['name']},")
            seen_cols.add(out_name)
            ddl_cols.append({"name": out_name, "type": c.get("type") or "String",
                             "from_entity": name, "source_col": c["name"],
                             "pk": "PK" in (c.get("flags") or [])})
    if select_cols and select_cols[-1].endswith(","):
        select_cols[-1] = select_cols[-1][:-1]

    sql_lines = ["SELECT"] + select_cols + [f"FROM {base}"]
    for j in joins:
        sql_lines.append(f"LEFT JOIN {j['table']} ON {j['condition']}"
                         + (f"  -- {j['label']}" if j["label"] else ""))
    join_sql = "\n".join(sql_lines)

    table_name = f"{base}_wide"
    order_keys = [c["name"] for c in ddl_cols
                  if c["pk"] and c["from_entity"] == base] or \
                 ([ddl_cols[0]["name"]] if ddl_cols else [])
    purpose = (purposes or {}).get(base, {}).get("purpose", "")
    ddl_lines = [f"CREATE TABLE {table_name} ("]
    for i, c in enumerate(ddl_cols):
        comma = "," if i < len(ddl_cols) - 1 else ""
        comment = f" COMMENT '來源 {c['from_entity']}.{c['source_col']}'"
        ddl_lines.append(f"  {c['name']} {c['type']}{comment}{comma}")
    ddl_lines.append(") ENGINE = MergeTree")
    if order_keys:
        ddl_lines.append(f"ORDER BY ({', '.join(order_keys)})")
    if purpose:
        first_line = purpose.splitlines()[0][:80]
        ddl_lines.append(f"COMMENT '{first_line}'")
    proposed_ddl = "\n".join(ddl_lines)

    # 與 input DDL 逐欄對比
    comparison = []
    for c in ddl_cols:
        located = sorted(t.name for t in schema.tables
                         if t.col(c["source_col"]) is not None)
        comparison.append({"column": c["name"], "type": c["type"],
                           "from_entity": c["from_entity"],
                           "in_input": located})
    proposed_names = {c["source_col"] for c in ddl_cols}
    input_only = []
    for t in schema.tables:
        for col in t.columns:
            if col.name not in proposed_names:
                input_only.append({"table": t.name, "column": col.name,
                                   "type": col.raw_type})

    return {
        "base_table": base,
        "table_name": table_name,
        "entities": join_order,
        "anchors": anchors,
        "not_in_input": sorted(n for n in join_order
                               if n.lower() not in input_tables),
        "join_sql": join_sql,
        "proposed_ddl": proposed_ddl,
        "comparison": comparison,
        "input_only": input_only,
        "warnings": warnings,
        "sources": sorted({entities[n].get("source") for n in join_order
                           if entities[n].get("source")}),
    }
