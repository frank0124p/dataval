"""跨表 join key 相容性（型別＋樣本編碼）— 由舊 SSOT.JOIN_KEY_* 搬遷。
強相關同檔：型別一致（可擋）＋值編碼一致（警告，需樣本）。"""
from collections import defaultdict
from dataval.model import Finding, ZONE_GATING

SKILL_META = {"id": "ssot_join_keys", "domain": "common",
              "category": "ssot", "zone": ZONE_GATING}


def _shape(vals):
    s0 = vals[0]
    if isinstance(s0, int):
        return "int"
    s = str(s0)
    if s.isdigit():
        return f"digits_len{len(s)}" + ("_zeropad" if s[0] == "0" and len(s) > 1 else "")
    if "-" in s and len(s) in (32, 36):
        return "uuid"
    return f"str_len{len(s)}"


def check_schema(schema, ctx):
    out = []
    ssot = ctx["cfg"].get("ssot") or {}
    declared = {m.get("key") for m in (ssot.get("registry") or {}).values() if m.get("key")}
    suffixes = tuple(ssot.get("join_key_suffixes", ["_id"]))
    keys = defaultdict(list)
    for t in schema.tables:
        for c in t.columns:
            if c.name in declared or c.name.endswith(suffixes):
                keys[c.name].append((t.name, c.base_type, c.raw_type))
    for key, occ in keys.items():
        if len(occ) > 1 and len({bt for _, bt, _ in occ}) > 1:
            out.append(Finding("SKILL.ssot_join_keys", "ssot", "fail", key,
                               f"Join key 型別一致：'{key}' 跨表型別不一致 "
                               f"{[(tn, bt) for tn, bt, _ in occ]}。",
                               rationale="型別不符的跨域 join 不安全。",
                               expected=f"'{key}' 在所有表同一 base type",
                               actual="；".join(f"{tn}:{bt}" for tn, bt, _ in occ),
                               fix="統一型別（建議與權威表一致）",
                               evidence=[{"table": tn, "type": rt} for tn, _, rt in occ]))
        elif len(occ) > 1:
            out.append(Finding("SKILL.ssot_join_keys", "ssot", "pass", key,
                               f"Join key 型別一致：'{key}' 於 {len(occ)} 表型別一致。"))
        shapes = {}
        for tn, _, _ in occ:
            vals = [r.get(key) for r in schema.sample_data.get(tn, []) if r.get(key) is not None]
            if vals:
                shapes[tn] = _shape(vals)
        if len(set(shapes.values())) > 1:
            out.append(Finding("SKILL.ssot_join_keys", "ssot", "warning", key,
                               f"Join key 值編碼：'{key}' 樣本值形態不一 {shapes}。",
                               severity="warning",
                               rationale="編碼不一（如補零與否）會讓 join 對不上。",
                               evidence=shapes))
    return out
