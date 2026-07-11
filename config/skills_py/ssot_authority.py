"""SSOT 權威唯一性（依 registry，跨表）— 由舊 SSOT.AUTHORITY_* 搬遷。
強相關同檔：權威表在場檢視 + 權威唯一性。"""
from dataval.model import Finding, ZONE_GATING

SKILL_META = {"id": "ssot_authority", "domain": "Common",
              "category": "ssot", "zone": ZONE_GATING}


def check_schema(schema, ctx):
    out = []
    registry = (ctx["cfg"].get("ssot") or {}).get("registry") or {}
    for entity, meta in registry.items():
        auth, key = meta.get("authoritative_table"), meta.get("key")
        if auth and schema.table(auth) is None:
            out.append(Finding("SKILL.ssot_authority", "ssot", "warning", auth,
                               f"權威表在場檢視：'{entity}' 的權威表不在本次 DDL。",
                               severity="info",
                               rationale="若它屬於另一 domain 的 schema 則屬正常。"))
        if not key:
            continue
        owners = []
        for t in schema.tables:
            if t.name == auth or t.col(key) is None:
                continue
            dup = [a for a in meta.get("attributes", []) if t.col(a) is not None]
            if dup:
                owners.append((t.name, dup))
        for tname, attrs in owners:
            out.append(Finding("SKILL.ssot_authority", "ssot", "fail", tname,
                               f"權威唯一性：此表重複承載 '{entity}' 的權威屬性 {attrs}"
                               f"（權威表：{auth}）。應引用而非複製。",
                               rationale="同一實體兩個擁有者破壞單一真實源。",
                               expected=f"'{entity}' 的屬性只在權威表 {auth} 落地",
                               actual=f"{tname} 重複承載 {attrs}",
                               fix=f"移除 {attrs}，改以 {key} 關聯 {auth}"))
        if auth and schema.table(auth) is not None and not owners:
            out.append(Finding("SKILL.ssot_authority", "ssot", "pass", auth,
                               f"權威唯一性：'{entity}' 只有單一權威擁有者。"))
    return out
