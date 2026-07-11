"""FK 目標必須存在（跨表）— 由舊 STRUCT.FK_RESOLVES 搬遷。"""
from dataval.model import Finding, ZONE_GATING

SKILL_META = {"id": "structural_fk_resolves", "domain": "common", "category": "structural",
              "zone": ZONE_GATING, "empty_status": "skipped",
              "empty_message": "structural_fk_resolves：本次 schema 沒有可檢查的 FK。"}


def check_schema(schema, ctx):
    out = []
    names = {t.name for t in schema.tables}
    for t in schema.tables:
        for fk in t.foreign_keys:
            tgt = f"{t.name}.{fk.columns}"
            if fk.ref_table not in names:
                out.append(Finding("SKILL.structural_fk_resolves", "structural", "fail", tgt,
                                   f"FK 目標不存在：引用了未知的表 '{fk.ref_table}'。",
                                   rationale="懸空外鍵破壞參照完整性。",
                                   expected="FK 引用的表存在於 schema",
                                   actual=f"'{fk.ref_table}' 不存在",
                                   fix="修正引用目標或補上該表定義"))
                continue
            ref = schema.table(fk.ref_table)
            bad = [c for c in fk.ref_columns if ref.col(c) is None]
            if bad:
                out.append(Finding("SKILL.structural_fk_resolves", "structural", "fail", tgt,
                                   f"FK 目標不存在：'{fk.ref_table}' 沒有欄位 {bad}。"))
            else:
                out.append(Finding("SKILL.structural_fk_resolves", "structural", "pass", tgt,
                                   "FK 目標解析：目標存在。"))
    return out
