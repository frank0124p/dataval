"""正式區（promoted zone）跨 domain 對照檢查。

正式區 promoted/<domain>/*.sql 放「已認可、已上線」的 DDL，作為命名與設計的基準。

當這次驗證的是「跨 domain 的 data subject」（載入了一個以上的非 common domain），
本檢查會把被驗證的 schema 對照正式區既有的 DDL，主要看：

  跨域命名一致性：同一個概念（以欄位名為代表）在正式區已經叫什麼，
  這份新設計就應該沿用相同名稱；若同概念用了不同名字，報為違規（會擋）。

這是確定性檢查（純字串比對既有 DDL），進閘門區、可會擋。
"""
from __future__ import annotations
import os
import re
from .model import Schema, Finding, ZONE_GATING
from .parser import parse_ddl


def _load_promoted(promoted_root: str, dialect: str = "clickhouse") -> dict:
    """Return {column_name: set(table_names)} aggregated across all promoted DDLs,
    plus {column_name: representative_table} for messaging."""
    col_owners: dict[str, set] = {}
    if not promoted_root or not os.path.isdir(promoted_root):
        return col_owners
    for dom in sorted(os.listdir(promoted_root)):
        dpath = os.path.join(promoted_root, dom)
        if not os.path.isdir(dpath):
            continue
        for fn in sorted(os.listdir(dpath)):
            if not fn.lower().endswith((".sql", ".ddl")):
                continue
            try:
                sch = parse_ddl(open(os.path.join(dpath, fn), encoding="utf-8").read(),
                                dialect=dialect)
            except Exception:
                continue
            for t in sch.tables:
                for c in t.columns:
                    col_owners.setdefault(c.name, set()).add(f"{dom}/{t.name}")
    return col_owners


# concept root = strip a known leading/trailing qualifier to find the "concept"
# e.g. customer_email -> email-of-customer; we compare by a normalized concept key
def _concept_key(col: str, glossary: dict | None = None) -> str:
    glossary = glossary or {}
    aliases = {k.lower(): v.lower() for k, v in (glossary.get("aliases") or {}).items()}
    banned = {k.lower(): v.lower() for k, v in (glossary.get("banned_terms") or {}).items()}
    toks = re.split(r"[_\s]+", col.lower())
    drop = {"id", "no", "code", "at", "by", "ts", "dt"}
    core = []
    for t in toks:
        if not t or t in drop:
            continue
        # normalize through glossary so client==customer, cust==customer, etc.
        t = aliases.get(t, banned.get(t, t))
        core.append(t)
    return "_".join(sorted(core)) if core else "_".join(toks)


def run(schema: Schema, cfg: dict, promoted_root: str,
        domains_loaded: list[str], dialect: str = "clickhouse",
        glossary: dict | None = None) -> list[Finding]:
    # only act when this is a cross-domain data subject
    non_common = [d for d in (domains_loaded or []) if d != "common"]
    if len(non_common) < 2:
        return [Finding("PROMOTED.SCOPE", "ssot", "skipped", "(promoted)",
                        "非跨 domain（或未指定多 domain），略過正式區對照。",
                        severity="info", source="rule", zone=ZONE_GATING)]

    promoted_cols = _load_promoted(promoted_root, dialect)
    if not promoted_cols:
        return [Finding("PROMOTED.SCOPE", "ssot", "skipped", "(promoted)",
                        "正式區無可對照的 DDL，略過。", severity="info",
                        source="rule", zone=ZONE_GATING)]

    # build concept -> promoted column-name(s), normalized through glossary
    concept_to_names: dict[str, set] = {}
    for col in promoted_cols:
        concept_to_names.setdefault(_concept_key(col, glossary), set()).add(col)

    out: list[Finding] = []
    checked = set()
    for t in schema.tables:
        for c in t.columns:
            key = _concept_key(c.name, glossary)
            if key in concept_to_names:
                approved = concept_to_names[key]
                if c.name not in approved and (key, c.name) not in checked:
                    checked.add((key, c.name))
                    owners = sorted({o for nm in approved for o in promoted_cols[nm]})
                    out.append(Finding(
                        "PROMOTED.NAMING_CONSISTENCY", "naming", "fail",
                        f"{t.name}.{c.name}",
                        f"同概念在正式區已命名為 {sorted(approved)}（見 {owners}），"
                        f"此設計用了不一致的 '{c.name}'，跨 domain 應沿用既有命名。",
                        severity="error",
                        rationale="跨 domain data subject 須與正式區既有命名一致，避免同概念異名。",
                        expected=f"沿用正式區命名 {sorted(approved)}",
                        actual=f"使用了 '{c.name}'",
                        fix=f"將 '{c.name}' 改名為 {sorted(approved)[0]}",
                        source="rule", zone=ZONE_GATING))
    if not out:
        out.append(Finding("PROMOTED.NAMING_CONSISTENCY", "naming", "pass", "(promoted)",
                           "跨 domain 命名與正式區一致。", severity="info",
                           source="rule", zone=ZONE_GATING))
    return out
