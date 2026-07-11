"""宣告型別 vs 樣本資料一致（需樣本）— 由舊 STRUCT.TYPE_SAMPLE_MATCH 搬遷。"""
from dataval.model import Finding, ZONE_GATING

SKILL_META = {"id": "structural_type_sample", "domain": "common",
              "category": "structural", "zone": ZONE_GATING}


def check_schema(schema, ctx):
    out = []
    checked = 0
    for t in schema.tables:
        for row in schema.sample_data.get(t.name, []):
            for col, val in row.items():
                c = t.col(col)
                if not c or val is None:
                    continue
                checked += 1
                tgt = f"{t.name}.{col}"
                if c.base_type == "int" and isinstance(val, float) and not val.is_integer():
                    out.append(Finding("SKILL.structural_type_sample", "structural", "fail",
                                       tgt, f"型別對樣本不符：宣告 int 但樣本有非整數 {val}。",
                                       evidence=val))
                if c.base_type in ("int", "decimal", "float") and isinstance(val, str):
                    try:
                        float(val)
                    except ValueError:
                        out.append(Finding("SKILL.structural_type_sample", "structural",
                                           "warning", tgt,
                                           f"型別對樣本不符：數值欄有非數值樣本 '{val}'。",
                                           severity="warning", evidence=val))
    if checked == 0:
        out.append(Finding("SKILL.structural_type_sample", "structural", "skipped",
                           "(sample)", "未提供可用的樣本值，略過型別對樣本檢查。",
                           severity="info"))
    elif not out:
        out.append(Finding("SKILL.structural_type_sample", "structural", "pass",
                           "(sample)", f"型別對樣本檢查：{checked} 個樣本值全數通過。",
                           severity="info"))
    return out
