"""同一事實不可散落多表（依 attribute_owner）— 由舊 SSOT.FACT_DUPLICATION 搬遷。"""
from collections import defaultdict
from dataval.model import Finding, ZONE_GATING

SKILL_META = {"id": "ssot_fact_duplication", "domain": "Common",
              "category": "ssot", "zone": ZONE_GATING}
_AUDIT = {"created_at", "updated_at", "created_by", "updated_by", "deleted_at"}


def check_schema(schema, ctx):
    out = []
    ssot = ctx["cfg"].get("ssot") or {}
    declared = {m.get("key") for m in (ssot.get("registry") or {}).values() if m.get("key")}
    owner = ssot.get("attribute_owner") or {}
    ignore = set(ssot.get("shared_columns_ok", [])) | declared | _AUDIT
    # 這裡的後綴清單是**排除用**（鍵欄本來就會跨表重複，不算事實重複），
    # 不是卡控清單。舊名 join_key_suffixes 仍相容。
    suffixes = tuple(ssot.get("key_like_suffixes")
                     or ssot.get("join_key_suffixes")
                     or ["_id", "_cd", "_no"])
    attr_tables = defaultdict(list)
    for t in schema.tables:
        for c in t.columns:
            if c.name not in ignore and not c.name.endswith(suffixes):
                attr_tables[c.name].append(t.name)
    for attr, tables in attr_tables.items():
        if len(tables) <= 1:
            continue
        if attr in owner:
            out.append(Finding("SKILL.ssot_fact_duplication", "ssot", "warning", attr,
                               f"事實重複：'{attr}' 出現在 {tables}；宣告擁有者為 "
                               f"'{owner[attr]}'，其餘表應由它同步衍生。",
                               severity="warning", rationale="重複事實會漂移失同步。"))
        else:
            out.append(Finding("SKILL.ssot_fact_duplication", "ssot", "fail", attr,
                               f"事實重複：'{attr}' 散落多表 {tables} 且無宣告擁有者。"
                               f"請指定單一真實源。",
                               rationale="重複事實會漂移失同步。",
                               expected=f"'{attr}' 只在單一權威表落地",
                               actual=f"散落於 {tables}",
                               fix="於 config/default.yaml 的 ssot.attribute_owner 指定擁有者，或移除重複欄位"))
    return out
