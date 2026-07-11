"""Production baseline governance.

`production/<domain>/*.sql` stores approved production DDLs. Validation only
reads the explicitly selected non-Common domains and treats their column names
as the accepted baseline. A new DDL using a different name for the same
normalized concept is blocked by `PRODUCTION.NAMING_CONSISTENCY`.
"""
from __future__ import annotations
import os
import re
from .model import Schema, Finding, ZONE_GATING
from .parser import parse_ddl
from .skills import COMMON_DOMAIN


def _load_production(production_root: str, domains: list[str],
                     dialect: str = "clickhouse") -> tuple[dict, list[Finding]]:
    """Return approved column owners from the selected production domains."""
    col_owners: dict[str, set] = {}
    diagnostics: list[Finding] = []
    if not production_root or not os.path.isdir(production_root):
        return col_owners, diagnostics

    available = {
        name.lower(): name for name in os.listdir(production_root)
        if os.path.isdir(os.path.join(production_root, name))
    }
    for requested in sorted(domains):
        dom = available.get(requested.lower())
        if dom is None:
            continue
        dpath = os.path.join(production_root, dom)
        for fn in sorted(os.listdir(dpath)):
            if not fn.lower().endswith((".sql", ".ddl")):
                continue
            try:
                path = os.path.join(dpath, fn)
                with open(path, encoding="utf-8") as f:
                    sch = parse_ddl(f.read(), dialect=dialect)
            except Exception as e:
                diagnostics.append(Finding(
                    "SYSTEM.PRODUCTION_PARSE", "ssot", "fail",
                    os.path.join(dom, fn),
                    f"Production DDL 無法解析：{type(e).__name__}: {e}",
                    severity="error", source="rule", zone=ZONE_GATING,
                    expected="production DDL 可正確解析", actual=str(e),
                    fix=f"修正 production/{dom}/{fn}"))
                continue
            for t in sch.tables:
                for c in t.columns:
                    col_owners.setdefault(c.name, set()).add(f"{dom}/{t.name}")
    return col_owners, diagnostics


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


def run(schema: Schema, production_root: str, domains_loaded: list[str],
        dialect: str = "clickhouse",
        glossary: dict | None = None) -> list[Finding]:
    selected = [d for d in (domains_loaded or [])
                if d.lower() != COMMON_DOMAIN.lower()]
    if not selected:
        return [Finding("PRODUCTION.SCOPE", "ssot", "skipped", "(production)",
                        "未明確指定業務 domain，不參照 production 基準區。",
                        severity="info", source="rule", zone=ZONE_GATING)]

    production_cols, diagnostics = _load_production(
        production_root, selected, dialect)
    if diagnostics:
        return diagnostics
    if not production_cols:
        return [Finding(
            "PRODUCTION.SCOPE", "ssot", "skipped", "(production)",
            f"已指定 domain {selected}，但 production 中沒有可參照的 DDL。",
            severity="info", source="rule", zone=ZONE_GATING)]

    referenced = sorted({
        owner.split("/", 1)[0]
        for owners in production_cols.values()
        for owner in owners
    })
    out: list[Finding] = [Finding(
        "PRODUCTION.SCOPE", "ssot", "pass", "(production)",
        f"已參照 production domain：{referenced}。",
        severity="info", source="rule", zone=ZONE_GATING)]

    # Build concept -> approved column names, normalized through the glossary.
    concept_to_names: dict[str, set] = {}
    for col in production_cols:
        concept_to_names.setdefault(_concept_key(col, glossary), set()).add(col)

    violations: list[Finding] = []
    checked = set()
    for t in schema.tables:
        for c in t.columns:
            key = _concept_key(c.name, glossary)
            if key in concept_to_names:
                approved = concept_to_names[key]
                if c.name not in approved and (key, c.name) not in checked:
                    checked.add((key, c.name))
                    owners = sorted({
                        owner for name in approved
                        for owner in production_cols[name]
                    })
                    violations.append(Finding(
                        "PRODUCTION.NAMING_CONSISTENCY", "naming", "fail",
                        f"{t.name}.{c.name}",
                        f"同概念在 production 已命名為 {sorted(approved)}（見 {owners}），"
                        f"此設計使用不一致的 '{c.name}'。",
                        severity="error",
                        rationale="新設計應沿用已核准的 production 命名，避免同概念異名。",
                        expected=f"沿用 production 命名 {sorted(approved)}",
                        actual=f"使用了 '{c.name}'",
                        fix=f"將 '{c.name}' 改名為 {sorted(approved)[0]}",
                        source="rule", zone=ZONE_GATING))
    if violations:
        out.extend(violations)
    else:
        out.append(Finding(
            "PRODUCTION.NAMING_CONSISTENCY", "naming", "pass", "(production)",
            "新設計命名與 production 基準一致。", severity="info",
            source="rule", zone=ZONE_GATING))
    return out
