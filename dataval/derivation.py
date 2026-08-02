"""衍生 SQL（derivation.sql）：使用者實際的 Join SQL 成為正式輸入。

寬表 subject 的第五件選填輸入 `input/<名>/derivation.sql`——記載這張寬表
「實際上是怎麼 join 出來的」。以 sqlglot **確定性解析**（零 LLM）：

  1. 來源表與別名、join 種類與 ON 鍵、逐欄 provenance（輸出欄 ← 來源表.欄）
  2. 與 relations.yaml 交叉驗證：SQL 有 join 但未宣告 → 警告；
     宣告了但 SQL 沒 join → 提示（兩邊都不靜默）
  3. 與寬表 DDL 對照：SQL 輸出欄 vs DDL 欄位的覆蓋（缺／多）
  4. 與建議 SQL（proposal）三方對照：join 鍵在
     「你的 SQL ↔ relations.yaml ↔ 建議 SQL」三處的出現矩陣

檢查結果為確定性閘門警告（不擋）＋報告專區；SQL 全文進迭代歷史
（input 變更追蹤與初終版 diff 一併涵蓋）。
"""
from __future__ import annotations

import sqlglot
from sqlglot import expressions as exp

from .model import Finding, ZONE_GATING


# ---------------------------------------------------------------- 解析

def parse_derivation(sql_text: str, dialect: str = "clickhouse") -> dict:
    """解析衍生 SQL。格式問題丟 ValueError（呼叫端降級為警告，不擋）。

    接受純 SELECT；CREATE TABLE … AS SELECT／INSERT INTO … SELECT
    會自動取出內層 SELECT。"""
    statements = [s for s in sqlglot.parse(sql_text, read=dialect)
                  if s is not None]
    if not statements:
        raise ValueError("沒有可解析的 SQL 陳述式")
    if len(statements) > 1:
        raise ValueError(f"只能有一個陳述式（實得 {len(statements)} 個）")
    node = statements[0]
    select = node if isinstance(node, exp.Select) else node.find(exp.Select)
    if select is None:
        raise ValueError("找不到 SELECT（衍生 SQL 必須是查詢）")

    # 別名 → 實表名（含 FROM 與所有 JOIN）
    aliases: dict[str, str] = {}
    for t in select.find_all(exp.Table):
        aliases[t.alias_or_name.lower()] = t.name
        aliases.setdefault(t.name.lower(), t.name)

    def resolve(alias: str) -> str:
        return aliases.get((alias or "").lower(), alias or "")

    # sqlglot 版本差異：from 參數鍵可能是 "from" 或 "from_"
    from_expr = select.args.get("from") or select.args.get("from_")
    base_table = ""
    if from_expr is not None and isinstance(from_expr.this, exp.Table):
        base_table = from_expr.this.name

    joins: list[dict] = []
    for j in select.args.get("joins") or []:
        join_table = j.this.name if isinstance(j.this, exp.Table) else ""
        on = j.args.get("on")
        keys = []
        if on is not None:
            for eq in on.find_all(exp.EQ):
                left, right = eq.left, eq.right
                if isinstance(left, exp.Column) and isinstance(right, exp.Column):
                    keys.append({"left_table": resolve(left.table),
                                 "left_column": left.name,
                                 "right_table": resolve(right.table),
                                 "right_column": right.name})
        joins.append({
            "table": join_table,
            "kind": " ".join(x for x in (j.side, j.kind) if x) or "JOIN",
            "keys": keys,
            "condition": on.sql(dialect=dialect) if on is not None else "",
        })

    outputs: list[dict] = []
    has_star = False
    for e in select.expressions:
        inner = e.this if isinstance(e, exp.Alias) else e
        if isinstance(e, exp.Star) or isinstance(inner, exp.Star):
            has_star = True
            continue
        if isinstance(inner, exp.Column) and isinstance(inner.this, exp.Star):
            has_star = True
            continue
        name = e.alias_or_name
        if isinstance(inner, exp.Column):
            outputs.append({"name": name, "kind": "column",
                            "source_table": resolve(inner.table),
                            "source_column": inner.name})
        else:
            outputs.append({"name": name, "kind": "expression",
                            "source_table": "", "source_column": "",
                            "expr": inner.sql(dialect=dialect)[:120]})

    return {
        "sql": sql_text.strip(),
        "base_table": base_table,
        "source_tables": sorted(set(aliases.values())),
        "joins": joins,
        "outputs": outputs,
        "has_star": has_star,
    }


# ---------------------------------------------------------------- 鍵配對

def _key_pair(table_a: str, col_a: str, table_b: str, col_b: str) -> frozenset:
    return frozenset({(table_a.lower(), col_a.lower()),
                      (table_b.lower(), col_b.lower())})


def sql_join_pairs(derivation: dict) -> set[frozenset]:
    pairs: set[frozenset] = set()
    for j in derivation.get("joins") or []:
        for k in j.get("keys") or []:
            pairs.add(_key_pair(k["left_table"], k["left_column"],
                                k["right_table"], k["right_column"]))
    return pairs


def declared_pairs(relations: list | None) -> set[frozenset]:
    """relations.yaml 的宣告 → 鍵配對集合（外部端點忽略 domain 前綴）。"""
    pairs: set[frozenset] = set()
    for rel in relations or []:
        src, dst = rel.get("_from"), rel.get("_to")
        if not src or not dst:
            continue
        pairs.add(_key_pair(src["table"], src["column"],
                            dst["table"], dst["column"]))
    return pairs


def proposal_pairs(ddl_proposal: dict | None) -> set[frozenset]:
    """建議 SQL 的 join 鍵——直接取 proposal 的結構化 join_pairs，
    不重新解析 SQL 文字。"""
    return {_key_pair(a[0], a[1], b[0], b[1])
            for a, b in (ddl_proposal or {}).get("join_pairs") or []}


def _pair_label(pair: frozenset) -> str:
    sides = sorted(f"{t}.{c}" for t, c in pair)
    return " = ".join(sides)


# ---------------------------------------------------------------- 對照層

def _pick_wide_table(schema, outputs: list[dict]):
    """挑欄位名重疊最高的 input 表當寬表（平手取名稱序；零重疊回 None）。"""
    out_names = {o["name"].lower() for o in outputs}
    best, best_overlap = None, 0
    for table in sorted(schema.tables, key=lambda t: t.name):
        overlap = len(out_names & {c.name.lower() for c in table.columns})
        if overlap > best_overlap:
            best, best_overlap = table, overlap
    return best


def derivation_layer(schema, derivation: dict | None,
                     problems: list[str] | None,
                     relations: list | None,
                     ddl_proposal: dict | None,
                     file_label: str = "derivation.sql"
                     ) -> tuple[list[Finding], dict | None]:
    """衍生 SQL 的確定性對照。回傳 (findings, meta 區塊或 None)。"""
    findings: list[Finding] = []
    for problem in problems or []:
        findings.append(Finding(
            "DERIVATION.PARSE", "structural", "warning", file_label,
            f"衍生 SQL 無法解析（已略過對照）：{problem}",
            severity="warning", source="rule", zone=ZONE_GATING,
            fix="修正 derivation.sql（單一 SELECT；CREATE AS／INSERT SELECT 亦可）"))
    if not derivation:
        return findings, None

    yours = sql_join_pairs(derivation)
    declared = declared_pairs(relations)
    suggested = proposal_pairs(ddl_proposal)

    undeclared = sorted(_pair_label(p) for p in yours - declared)
    unused_declared = sorted(_pair_label(p) for p in declared - yours)
    if undeclared:
        findings.append(Finding(
            "DERIVATION.RELATIONS", "structural", "warning", file_label,
            f"SQL 有 join 但 relations.yaml 未宣告：{undeclared}。",
            severity="warning", source="rule", zone=ZONE_GATING,
            expected="derivation 的每組 join 鍵都在 relations.yaml 宣告",
            actual=f"未宣告 {len(undeclared)} 組",
            fix="把這些 join 鍵補進 relations.yaml（跨 domain 用三段式端點）"))
    elif yours:
        findings.append(Finding(
            "DERIVATION.RELATIONS", "structural", "pass", file_label,
            f"衍生 SQL 的 {len(yours)} 組 join 鍵皆已在 relations.yaml 宣告。",
            severity="info", source="rule", zone=ZONE_GATING))
    if unused_declared:
        findings.append(Finding(
            "DERIVATION.RELATIONS", "structural", "info", file_label,
            f"relations.yaml 有宣告、但衍生 SQL 未使用的關聯：{unused_declared}。",
            severity="info", source="rule", zone=ZONE_GATING,
            fix="確認是刻意未用（如僅供 lineage）或 SQL 漏了 join"))

    coverage = None
    wide = _pick_wide_table(schema, derivation.get("outputs") or [])
    if wide is not None:
        out_names = {o["name"].lower() for o in derivation["outputs"]}
        ddl_names = {c.name.lower() for c in wide.columns}
        missing_in_sql = sorted(ddl_names - out_names)
        extra_in_sql = sorted(out_names - ddl_names)
        coverage = {"wide_table": wide.name,
                    "covered": len(ddl_names & out_names),
                    "ddl_columns": len(ddl_names),
                    "missing_in_sql": missing_in_sql,
                    "extra_in_sql": extra_in_sql,
                    "has_star": derivation.get("has_star", False)}
        if derivation.get("has_star"):
            findings.append(Finding(
                "DERIVATION.COVERAGE", "structural", "info", wide.name,
                "衍生 SQL 使用 SELECT *，無法逐欄對照 provenance；"
                "建議展開明確欄位清單。",
                severity="info", source="rule", zone=ZONE_GATING))
        elif missing_in_sql or extra_in_sql:
            findings.append(Finding(
                "DERIVATION.COVERAGE", "structural", "warning", wide.name,
                f"衍生 SQL 輸出與寬表 `{wide.name}` 欄位不一致："
                f"DDL 有但 SQL 沒產出 {missing_in_sql or '（無）'}；"
                f"SQL 產出但 DDL 沒有 {extra_in_sql or '（無）'}。",
                severity="warning", source="rule", zone=ZONE_GATING,
                expected="SQL 輸出欄 ＝ 寬表 DDL 欄位",
                actual=f"缺 {len(missing_in_sql)}、多 {len(extra_in_sql)}",
                fix="同步 derivation.sql 與 DDL（欄位增減要兩邊一起改）"))
        else:
            findings.append(Finding(
                "DERIVATION.COVERAGE", "structural", "pass", wide.name,
                f"衍生 SQL 輸出與寬表 `{wide.name}` 逐欄一致"
                f"（{len(ddl_names)} 欄全數對上）。",
                severity="info", source="rule", zone=ZONE_GATING))

    # join 鍵三方矩陣（報告呈現用）
    matrix = []
    for pair in sorted(yours | declared | suggested, key=_pair_label):
        matrix.append({"pair": _pair_label(pair),
                       "in_sql": pair in yours,
                       "in_relations": pair in declared,
                       "in_proposal": pair in suggested})

    meta = {"file": file_label,
            "base_table": derivation.get("base_table", ""),
            "source_tables": derivation.get("source_tables", []),
            "join_count": len(derivation.get("joins") or []),
            "output_count": len(derivation.get("outputs") or []),
            "expression_count": sum(
                1 for o in derivation.get("outputs") or []
                if o["kind"] == "expression"),
            "sql": derivation.get("sql", ""),
            "coverage": coverage,
            "key_matrix": matrix,
            "has_proposal": bool(suggested)}
    return findings, meta
