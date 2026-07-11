"""Skill loading layer.

A skill = scope + logic + category + severity + rationale. It is NOT a fifth
check category; it loads into one of the existing four (structural | naming |
best_practice | ssot). Two authoring forms (hybrid):

  - Declarative (YAML): domain experts write conditions, no code. Deterministic,
    so these run in the GATING zone (can block).
  - Imperative (Python): a function check(schema, table) -> list[Finding] for
    complex logic. Declares its own zone.

Skills are .md spec files (parsed by markdown_skill) plus python skills.
"""
from __future__ import annotations
import importlib.util
import os
import re
from ..model import Schema, Table, Finding, ZONE_GATING

VALID_CATEGORIES = {"structural", "naming", "best_practice", "ssot"}



def _table_matches(t: Table, applies: dict) -> bool:
    if not applies:
        return True
    if "name_matches" in applies and not re.search(applies["name_matches"], t.name):
        return False
    if "has_column" in applies and t.col(applies["has_column"]) is None:
        return False
    if "has_engine" in applies:
        if not t.engine or applies["has_engine"].lower() not in t.engine.lower():
            return False
    return True


def _eval_require(t: Table, req: dict) -> tuple[bool, str]:
    """Return (passed, detail_if_failed)."""
    if "has_column" in req:
        ok = t.col(req["has_column"]) is not None
        return ok, f"缺少必要欄位 '{req['has_column']}'"
    if "column_type" in req:
        spec = req["column_type"]  # {column: x, base_type: y}
        c = t.col(spec["column"])
        if c is None:
            return True, ""  # absence handled by has_column elsewhere
        ok = c.base_type == spec["base_type"]
        return ok, f"欄位 '{spec['column']}' 型別應為 {spec['base_type']}，實際 {c.base_type}"
    if "not_nullable" in req:
        c = t.col(req["not_nullable"])
        if c is None:
            return True, ""
        return (not c.nullable), f"欄位 '{req['not_nullable']}' 不應為 Nullable"
    if "columns_not_both" in req:
        pair = req["columns_not_both"]
        both = t.col(pair[0]) is not None and t.col(pair[1]) is not None
        return (not both), f"欄位 '{pair[0]}' 與 '{pair[1]}' 不應同時存在"
    if "name_matches" in req:
        spec = req["name_matches"]  # {column: x, pattern: y}
        c = t.col(spec["column"])
        if c is None:
            return True, ""
        ok = re.fullmatch(spec["pattern"], c.name) is not None
        return ok, f"欄位 '{spec['column']}' 不符命名樣式 {spec['pattern']}"
    return True, ""



class SkillRegistry:
    def __init__(self):
        self.markdown: list = []                       # .md skills (rule or llm)
        self.imperative: list = []  # modules exposing SKILL_META + check()
        self.loaded_domains: list[str] = []
        self.loaded_rule_ids: list[str] = []
        self.requested_domains: list[str] = []
        self.unknown_domains: list[str] = []

    def load_compiled(self, compiled_path: str, domains: list[str] | None = None,
                      config_dir: str = "config"):
        """從 build/compiled_rules.json 載入規則來執行（整合進主流程的 build 產物）。
        common 一律載入；未指定 domain 時只載入 common。
        明確傳入 ["*"] 才載入全部。py 規則也依 manifest domain 過濾。"""
        import json
        from .markdown_skill import skill_from_compiled
        with open(compiled_path, encoding="utf-8") as f:
            data = json.load(f)
        requested = [d.strip() for d in (domains or []) if d and d.strip()]
        load_all = any(d.lower() in ("*", "all") for d in requested)
        wanted = {d.lower() for d in requested if d.lower() not in ("*", "all")}
        self.requested_domains = requested
        known = {str(d).lower(): str(d) for d in (data.get("domains") or [])}
        self.unknown_domains = sorted(d for d in requested
                                      if d.lower() not in known and d.lower() not in ("*", "all"))
        loaded = set()
        for e in data.get("rules", []):
            dom = e.get("domain", "?")
            if dom != "common" and not load_all and dom.lower() not in wanted:
                continue
            if e.get("kind") == "python":
                path = os.path.join(config_dir, e["file"].replace("skills_py/", "skills_py" + os.sep))
                spec = importlib.util.spec_from_file_location(
                    os.path.splitext(os.path.basename(path))[0], path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "SKILL_META") and (
                        hasattr(mod, "check") or hasattr(mod, "check_schema")):
                    self.imperative.append(mod)
                    self.loaded_rule_ids.append(f"SKILL.{e.get('id', mod.__name__)}")
                continue
            self.markdown.append(skill_from_compiled(e))
            self.loaded_rule_ids.append(f"SKILL.{e['id']}")
            loaded.add(dom)
        all_domains = data.get("domains") or sorted(
            {e.get("domain") for e in data.get("rules", []) if e.get("kind") != "python"})
        if load_all:
            chosen = list(all_domains)
        else:
            chosen = [d for d in all_domains
                      if d == "common" or d.lower() in wanted]
            if "common" not in chosen and "common" in all_domains:
                chosen.append("common")
        self.loaded_domains = sorted(chosen)
        self.loaded_rule_ids = sorted(set(self.loaded_rule_ids))

    def load_domains(self, skills_root: str, domains: list[str] | None = None,
                     py_dir: str = ""):
        """Load skills from a domain-structured root:

            skills_root/<domain>/{gating,advisory}/*.md

        `common` is ALWAYS loaded. This authoring/compiler path loads every domain
        when `domains` is None;
        otherwise only the named domains (plus common). Each .md self-declares
        gating vs advisory via its enforcement/check-block, so the gating/advisory
        subfolders are organisational — the zone still comes from the file.
        """
        from .markdown_skill import load_markdown_skill
        if not skills_root or not os.path.isdir(skills_root):
            return
        all_domains = sorted(d for d in os.listdir(skills_root)
                             if os.path.isdir(os.path.join(skills_root, d)))
        if domains is None:
            chosen = all_domains
        else:
            wanted = {d.strip() for d in domains if d.strip()}
            chosen = [d for d in all_domains
                      if d == "common" or d in wanted or d.lower() in {w.lower() for w in wanted}]
            if "common" not in chosen and "common" in all_domains:
                chosen.append("common")
        self.loaded_domains = chosen
        for dom in chosen:
            dom_path = os.path.join(skills_root, dom)
            for sub in ("gating", "advisory"):
                subdir = os.path.join(dom_path, sub)
                if os.path.isdir(subdir):
                    for fn in sorted(os.listdir(subdir)):
                        if fn.endswith(".md"):
                            sk = load_markdown_skill(os.path.join(subdir, fn))
                            sk.domain = dom
                            self.markdown.append(sk)
                            self.loaded_rule_ids.append(f"SKILL.{sk.id}")
            # also allow loose .md directly under the domain (no subfolder)
            for fn in sorted(os.listdir(dom_path)):
                full = os.path.join(dom_path, fn)
                if os.path.isfile(full) and fn.endswith(".md"):
                    sk = load_markdown_skill(full)
                    sk.domain = dom
                    self.markdown.append(sk)
                    self.loaded_rule_ids.append(f"SKILL.{sk.id}")
        if py_dir and os.path.isdir(py_dir):
            for fn in sorted(os.listdir(py_dir)):
                if fn.endswith(".py") and not fn.startswith("_"):
                    path = os.path.join(py_dir, fn)
                    spec = importlib.util.spec_from_file_location(fn[:-3], path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "SKILL_META") and (
                            hasattr(mod, "check") or hasattr(mod, "check_schema")):
                        self.imperative.append(mod)
                        self.loaded_rule_ids.append(
                            f"SKILL.{mod.SKILL_META.get('id', mod.__name__)}")
        self.loaded_rule_ids = sorted(set(self.loaded_rule_ids))


    def count(self) -> int:
        return len(self.markdown) + len(self.imperative)

    def run(self, schema: Schema, llm=None, glossary: dict | None = None,
            cfg: dict | None = None) -> list[Finding]:
        out: list[Finding] = []
        ctx = {"cfg": cfg or {}, "glossary": glossary or {}}
        for s in self.markdown:
            out.extend(s.run(schema, llm, glossary))  # rule uses glossary; llm-mode uses llm
        for mod in self.imperative:
            meta = mod.SKILL_META
            found: list[Finding] = []
            # schema-level rule: runs ONCE per schema (cross-table logic)
            if hasattr(mod, "check_schema"):
                found.extend(mod.check_schema(schema, ctx) or [])
            # per-table rule: check(schema, table) or check(schema, table, ctx)
            if hasattr(mod, "check"):
                import inspect
                takes_ctx = len(inspect.signature(mod.check).parameters) >= 3
                for t in schema.tables:
                    found.extend((mod.check(schema, t, ctx) if takes_ctx
                                  else mod.check(schema, t)) or [])
            if not found:
                rule_id = meta.get("id", mod.__name__)
                empty_status = meta.get("empty_status", "pass")
                found.append(Finding(
                    f"SKILL.{rule_id}", meta.get("category", "structural"),
                    empty_status, "(schema)",
                    meta.get("empty_message", f"{rule_id}：已執行，未發現違規。"),
                    severity="info", source="skill",
                    zone=meta.get("zone", ZONE_GATING)))
            for f in found:
                f.source = "skill"
                f.category = meta.get("category", f.category)
                f.zone = meta.get("zone", ZONE_GATING)
                out.append(f)
        return out
