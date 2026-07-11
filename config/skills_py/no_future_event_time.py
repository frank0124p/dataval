"""Imperative skill: event_time-like columns should not allow obviously wrong
defaults. Demonstrates the code-based form for logic too complex for YAML."""
from dataval.model import Finding, ZONE_GATING

SKILL_META = {"id": "no_future_event_time", "domain": "Common",
              "category": "best_practice", "zone": ZONE_GATING}

def check(schema, table):
    out = []
    for c in table.columns:
        if c.base_type == "datetime" and c.default and "now" not in (c.default or "").lower():
            out.append(Finding(
                check_id="SKILL.no_future_event_time",
                category="best_practice", status="warning", target=f"{table.name}.{c.name}",
                message=f"時間欄位有靜態預設值 '{c.default}'，通常應為 now()。",
                severity="warning", rationale="靜態時間預設常是錯誤。"))
    return out
