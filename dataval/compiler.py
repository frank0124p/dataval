"""規則 compile：把 .md 規則轉成機器可讀的 JSON 中間格式。

.md 是「撰寫格式」（人讀規範＋卡控區塊）；compile 產出的
build/compiled_rules.json 是「執行格式」——結構化、可 diff、可稽核。

關鍵設計：
  1. 同一套解析：JSON 由 SkillSpec（引擎實際執行的解析結果）序列化而來，
     不存在第二套解析器，撰寫與執行永不分歧。
  2. 確定性：內容排序、無時間戳。規則沒變 → JSON 逐字不變。
  3. 可稽核：每條規則以明確的 checking rule ID 識別，不使用指紋或雜湊碼。
  4. 更新偵測：每次重新編譯後直接比對結構化內容，有變更才寫入。
"""
from __future__ import annotations
import json
import os
import sys


def compile_rules(domain_root: str, rules_root: str) -> dict:
    """Load every domain's skills through the real parser and serialize."""
    from .skills import COMMON_DOMAIN, SkillRegistry
    reg = SkillRegistry()
    reg.load_domains(domain_root, domains=None, rules_root=rules_root)

    rules = []
    for s in reg.markdown:
        entry = {
            "id": s.id,
            "domain": getattr(s, "domain", "?"),
            "zone": s.zone,
            "category": s.category,
            "enforcement": s.enforcement,
            "title": s.title,
            "purpose": s.prose.get("目的", ""),
            "fix_hint": getattr(s, "fix_hint", ""),
            "kind": "check" if s.check_lines else ("check-llm" if s.check_llm else "empty"),
            "applies_to": s.applies,
            "requires": s.requires,
            "check_llm": s.check_llm or "",
            "unparsed": s.unparsed,
            "file": os.path.relpath(
                s.path, os.path.dirname(domain_root)).replace(os.sep, "/"),
        }
        rules.append(entry)
    for m in reg.imperative:
        meta = m.SKILL_META
        entry = {
            "id": meta.get("id", m.__name__),
            "domain": meta.get("domain", COMMON_DOMAIN),
            "zone": meta.get("zone", "gating"),
            "category": meta.get("category", "?"),
            "enforcement": "python",
            "title": (m.__doc__ or "").strip().splitlines()[0] if m.__doc__ else "",
            "kind": "python",
            "file": os.path.relpath(
                m.__file__, os.path.dirname(domain_root)).replace(os.sep, "/"),
        }
        rules.append(entry)

    rules.sort(key=lambda r: (r["domain"], r["id"]))
    domains = sorted(d for d in os.listdir(domain_root)
                     if os.path.isdir(os.path.join(domain_root, d)))
    return {
        "format": "dataval.compiled_rules.v2",
        "domains": domains,
        "rule_count": len(rules),
        "rules": rules,
    }


def ensure_compiled(domain_root: str, rules_root: str,
                    out_path: str) -> tuple[str, bool]:
    """Compile rules and write only when the structured payload changed."""
    payload = compile_rules(domain_root, rules_root)
    if os.path.isfile(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                old = json.load(f)
            if old == payload:
                return out_path, False
        except Exception as e:
            print(f"規則 compile 快取無法讀取，將重建：{type(e).__name__}: {e}",
                  file=sys.stderr)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)
    return out_path, True
