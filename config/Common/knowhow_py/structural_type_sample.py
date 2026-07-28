"""宣告型別 vs 樣本資料一致（需樣本）— 由舊 STRUCT.TYPE_SAMPLE_MATCH 搬遷。

多列樣本命中同一欄位時**按欄位彙整**：一欄一筆 finding（fail 與 warning
各自一筆），訊息列出違規值與筆數——避免逐列刷版，報告一行看完一個欄位。
"""
from dataval.model import Finding, ZONE_GATING

SKILL_META = {"id": "structural_type_sample", "domain": "Common",
              "category": "structural", "zone": ZONE_GATING}

_SHOW = 5  # 訊息最多列出的違規值個數；其餘以「共 N 筆」帶過（evidence 保留全部）


def _preview(vals: list) -> str:
    shown = "、".join(repr(v) for v in vals[:_SHOW])
    if len(vals) > _SHOW:
        shown += f" …（共 {len(vals)} 筆）"
    return shown


def check_schema(schema, ctx):
    out = []
    checked = 0
    int_mismatch: dict[str, list] = {}   # 欄位 → 非整數樣本值（宣告 int）
    non_numeric: dict[str, list] = {}    # 欄位 → 非數值樣本值（宣告數值型別）
    for t in schema.tables:
        for row in schema.sample_data.get(t.name, []):
            for col, val in row.items():
                c = t.col(col)
                if not c or val is None:
                    continue
                checked += 1
                tgt = f"{t.name}.{col}"
                if c.base_type == "int" and isinstance(val, float) and not val.is_integer():
                    int_mismatch.setdefault(tgt, []).append(val)
                if c.base_type in ("int", "decimal", "float") and isinstance(val, str):
                    try:
                        float(val)
                    except ValueError:
                        non_numeric.setdefault(tgt, []).append(val)
    for tgt, vals in sorted(int_mismatch.items()):
        out.append(Finding("SKILL.structural_type_sample", "structural", "fail",
                           tgt,
                           f"型別對樣本不符：宣告 int 但樣本有 {len(vals)} 筆"
                           f"非整數值（{_preview(vals)}）。",
                           expected="樣本值皆為整數",
                           actual=f"{len(vals)} 筆非整數",
                           fix="修正樣本或把欄位型別改為 Decimal/Float",
                           evidence=vals))
    for tgt, vals in sorted(non_numeric.items()):
        out.append(Finding("SKILL.structural_type_sample", "structural",
                           "warning", tgt,
                           f"型別對樣本不符：數值欄有 {len(vals)} 筆非數值樣本"
                           f"（{_preview(vals)}）。",
                           severity="warning",
                           expected="樣本值皆可解析為數值",
                           actual=f"{len(vals)} 筆非數值",
                           fix="修正樣本值或檢視欄位型別宣告",
                           evidence=vals))
    if checked == 0:
        out.append(Finding("SKILL.structural_type_sample", "structural", "skipped",
                           "(sample)", "未提供可用的樣本值，略過型別對樣本檢查。",
                           severity="info"))
    elif not out:
        out.append(Finding("SKILL.structural_type_sample", "structural", "pass",
                           "(sample)", f"型別對樣本檢查：{checked} 個樣本值全數通過。",
                           severity="info"))
    return out
