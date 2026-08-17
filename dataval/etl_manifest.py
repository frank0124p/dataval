#!/usr/bin/env python3
"""ETL pipeline 建議檔（design mode 產物）——`reports/<名>.etl.yaml`。

未來系統內 ETL 需要的設定文件：這個 data subject 的 pipeline 識別碼、
所屬 product suite／namespace、來源與目標 DB、表名、用在哪個 database
（ex: clickhouse）、更新方式（insert／deleteInsert…）、CPU／Memory 配置、
更新頻率與 owner。

刻意的定位（與其他設計產物完全解耦）：

  - **純建議檔**：不進閘門、不影響任何合規判定、不被其他產物消費，
    也不消費其他產物的內容（表名除外——表名本來就是設計的結果）。
  - **沒資訊也長殼**：agent 起草的 `design_result.etl_pipeline` 沒給的欄位，
    仍然把 key 留在檔案裡（值留空＝YAML null）並在註解標 `TODO 待填`，
    拿到手就是一份可以直接改的骨架。
  - **缺的欄位進問答區**：工具確定性產生對應的設計提問，隨設計問答迴圈
    寫進 `input/<名>/design_answers.yaml`（status: proposed）請使用者填；
    使用者驗證後下一輪自動帶進 design prompt，agent 據以補完 etl_pipeline。

此模組零 LLM、純函式、輸出確定性（同輸入 → 位元組相同）。
"""
from __future__ import annotations

import re

#: 沒有資訊的欄位仍長出殼：值留空（YAML null）＋註解標這個字樣
TODO = "TODO 待填"

#: 預設的目標資料庫平台（本工具以 ClickHouse 為主；推導值會標 🤖 請確認）
DEFAULT_PLATFORM = "clickhouse"

#: 常見的更新方式（不是白名單——ETL 系統可自訂，這裡只做提示）
WRITE_MODES = ("insert", "deleteInsert", "upsert", "replace", "append")

#: pipeline（subject）層欄位：key、標籤、填寫提示
PIPELINE_FIELDS: tuple[dict, ...] = (
    {"key": "id", "label": "ETL pipeline 識別碼", "hint": "全域唯一的 ID"},
    {"key": "product_suite", "label": "所屬 product suite",
     "hint": "這個 data subject 屬於哪個產品線"},
    {"key": "namespace", "label": "namespace", "hint": "ETL 系統內的命名空間"},
    {"key": "platform", "label": "用在哪個 database",
     "hint": f"ex: {DEFAULT_PLATFORM}"},
    {"key": "source_db", "label": "來源 DB", "hint": "資料從哪個 DB 讀"},
    {"key": "target_db", "label": "目標 DB", "hint": "資料寫進哪個 DB"},
    {"key": "write_mode", "label": "更新方式",
     "hint": "｜".join(WRITE_MODES)},
    {"key": "schedule", "label": "更新頻率",
     "hint": "ex: daily 02:00、hourly、*/15 * * * *"},
    {"key": "cpu", "label": "CPU 配置", "hint": "ex: 2、1000m"},
    {"key": "memory", "label": "Memory 配置", "hint": "ex: 4Gi"},
    {"key": "owner", "label": "對應 owner", "hint": "負責人或團隊"},
)

#: 逐表（每張表一個 ETL job）覆寫欄位；沒覆寫就沿用 pipeline 層
TABLE_KEYS: tuple[str, ...] = ("id", "source_db", "target_db", "write_mode",
                               "schedule", "cpu", "memory", "owner")

#: 這兩個欄位在 YAML 裡收在 resources: 之下（agent 輸入格式亦同）
RESOURCE_KEYS: tuple[str, ...] = ("cpu", "memory")

#: 逐表層的標籤覆寫（同一個 key 在表層是「job」語意）
TABLE_LABELS = {"id": {"label": "ETL job 識別碼", "hint": "這張表的 job ID"}}

_FIELD_BY_KEY = {f["key"]: f for f in PIPELINE_FIELDS}

#: 來源標記：agent 宣告／context.md 推導／工具推導／沿用上層／沒有資訊
ORIGIN_MARK = {"agent": "", "context": "🤖 由 context.md 推導 ",
               "derived": "🤖 推導 ", "inherit": "↑ 沿用 pipeline 預設 ",
               "missing": ""}


# ---------------------------------------------------------------- 組裝

def _clean(value) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    return str(value).strip() if isinstance(value, (str, int, float)) else ""


def _read(src: dict, key: str) -> str:
    """讀一個欄位（cpu／memory 收在 resources 之下）。"""
    if not isinstance(src, dict):
        return ""
    if key in RESOURCE_KEYS:
        res = src.get("resources")
        return _clean(res.get(key)) if isinstance(res, dict) else ""
    return _clean(src.get(key))


def _slug(text: str) -> str:
    """subject 名 → 識別碼片段（非英數轉底線；中文主體名也能得到穩定 id）。"""
    out = re.sub(r"[^0-9a-zA-Z]+", "_", str(text)).strip("_").lower()
    return out or "subject"


def _field(key: str, value: str, origin: str,
           labels: dict | None = None) -> dict:
    spec = {**_FIELD_BY_KEY[key], **((labels or {}).get(key) or {})}
    return {"key": key, "label": spec["label"], "hint": spec["hint"],
            "value": value, "origin": origin if value else "missing"}


def build(subject: str, result: dict, meta: dict | None = None) -> dict:
    """確定性組出 ETL 建議檔的資料結構。

    值的優先序：agent 宣告（`design_result.etl_pipeline`）→ context.md
    front-matter 推導 → 工具推導 → 沒有資訊（missing，長殼＋進問答）。
    表清單以 physical_design 的表為準（表名是設計的結果，不另外問）。

    回傳 {"subject", "pipeline": {key: field}, "tables": [...],
          "missing": [key…]}——missing 是「pipeline 層或任一表仍缺」的欄位。
    """
    spec = result.get("etl_pipeline")
    spec = spec if isinstance(spec, dict) else {}
    meta = meta or {}

    context_values: dict[str, str] = {}
    product = _clean(meta.get("product"))
    if product:
        context_values["product_suite"] = product

    derived: dict[str, str] = {"id": f"etl_{_slug(subject)}",
                               "platform": DEFAULT_PLATFORM}

    pipeline: dict[str, dict] = {}
    for spec_field in PIPELINE_FIELDS:
        key = spec_field["key"]
        value, origin = _read(spec, key), "agent"
        if not value and key in context_values:
            value, origin = context_values[key], "context"
        if not value and key in derived:
            value, origin = derived[key], "derived"
        pipeline[key] = _field(key, value, origin)

    by_name = {}
    for entry in spec.get("tables") or []:
        if isinstance(entry, dict) and _clean(entry.get("table")):
            by_name[_clean(entry["table"]).lower()] = entry

    tables: list[dict] = []
    for table in (result.get("physical_design") or {}).get("tables") or []:
        if not isinstance(table, dict):
            continue
        tname = _clean(table.get("name"))
        if not tname:
            continue
        entry = by_name.get(tname.lower(), {})
        fields: dict[str, dict] = {}
        for key in TABLE_KEYS:
            value, origin = _read(entry, key), "agent"
            if not value and key == "id" and pipeline["id"]["value"]:
                value, origin = f"{pipeline['id']['value']}.{tname}", "derived"
            if not value and pipeline[key]["value"]:
                value, origin = pipeline[key]["value"], "inherit"
            fields[key] = _field(key, value, origin, TABLE_LABELS)
        tables.append({"table": tname,
                       "layer": _clean(table.get("layer")),
                       "comment": _clean(table.get("comment")),
                       "fields": fields})

    def _origins(key: str) -> list[str]:
        # 表層 id 一律由 pipeline id 推導（不是獨立資訊），不列入判斷——
        # 否則 pipeline id 已宣告，仍會因逐表推導值而重複發問。
        if key == "id":
            return [pipeline[key]["origin"]]
        return [pipeline[key]["origin"]] + [
            t["fields"][key]["origin"] for t in tables if key in TABLE_KEYS]

    missing = [f["key"] for f in PIPELINE_FIELDS
               if "missing" in _origins(f["key"])]
    # 待確認＝完全沒資訊（missing）＋工具自己推導出來的（derived，使用者
    # 沒說過的值）——兩者都進問答區請使用者填／確認。
    needs_input = [f["key"] for f in PIPELINE_FIELDS
                   if {"missing", "derived"} & set(_origins(f["key"]))]
    return {"subject": subject, "pipeline": pipeline, "tables": tables,
            "missing": missing, "needs_input": needs_input}


# ---------------------------------------------------------------- YAML 渲染

_PLAIN_RE = re.compile(r"^[0-9A-Za-z_][0-9A-Za-z_.\-/ ]*$")


def _scalar(value: str) -> str:
    """字串 → YAML 純量（含 `:`／`#`／引號等特殊字元時單引號包起來）。"""
    text = str(value)
    if _PLAIN_RE.match(text) and not text.endswith(" "):
        return text
    return "'" + text.replace("'", "''") + "'"


def _line(indent: str, key: str, field: dict) -> str:
    note = f"{field['label']}（{field['hint']}）"
    if field["origin"] == "missing":
        return f"{indent}{key}:{' ' * 2}# ⬅ {TODO}：{note}"
    return (f"{indent}{key}: {_scalar(field['value'])}"
            f"  # {ORIGIN_MARK.get(field['origin'], '')}{note}")


def _block(indent: str, fields: dict, keys) -> list[str]:
    """一組欄位 → YAML 行（resources 的兩個欄位收成子層）。"""
    out: list[str] = []
    for key in keys:
        if key in RESOURCE_KEYS:
            continue
        out.append(_line(indent, key, fields[key]))
    resource_keys = [k for k in keys if k in RESOURCE_KEYS]
    if resource_keys:
        out.append(f"{indent}resources:")
        out += [_line(indent + "  ", k, fields[k]) for k in resource_keys]
    return out


def to_yaml(subject: str, round_no: int, manifest: dict) -> str:
    """ETL 建議檔全文（確定性；沒有資訊的欄位留殼並標 TODO）。"""
    pipeline = manifest["pipeline"]
    lines = [
        f"# ETL pipeline 建議檔 — {subject}（第 {round_no} 輪設計）",
        "#",
        "# 🎨 design mode 的**建議檔**：未來系統內 ETL 需要的設定。",
        "# 這份檔案與其他設計產物沒有關聯——不進閘門、不影響任何判定，",
        "# 拿去改、改壞了都不會動到設計或治理結果。",
        "#",
        "# 標記：🤖＝工具推導的預設值（請確認）；",
        f"#       `# ⬅ {TODO}` ＝沒有資訊的欄位，值留空等你填。",
        f"# 缺的欄位已同步進設計問答 input/{subject}/design_answers.yaml——",
        "# 在那裡回答並驗證（proposed → answered），下一輪設計會自動補上。",
        "#",
        "# 每張表 = 一個 ETL job：table 區塊是自足的（沒覆寫就已展開 pipeline",
        "# 層的預設值），ETL 系統可逐 job 直接取用。",
        "",
        "version: 1",
        f"subject: {_scalar(subject)}",
        f"design_round: {round_no}",
        "",
        "# ── pipeline（本 data subject 的共同設定）",
    ]
    lines += _block("", pipeline, [f["key"] for f in PIPELINE_FIELDS])
    lines += ["", "# ── 每張表一個 ETL job"]
    if not manifest["tables"]:
        lines.append("tables: []  # ⬅ 設計尚無資料表")
        return "\n".join(lines) + "\n"
    lines.append("tables:")
    for table in manifest["tables"]:
        head = f"  - table: {_scalar(table['table'])}"
        note = "、".join(x for x in (table.get("layer"),
                                     table.get("comment")) if x)
        lines.append(head + (f"  # {note}" if note else ""))
        lines += _block("    ", table["fields"], TABLE_KEYS)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 設計問答

#: 缺欄位 → 設計提問（同群一題，避免一次丟十幾題）。提問文字必須跨輪穩定
#: （question_id 是文字的 hash），所以只帶 subject 名、不帶會變動的內容。
QUESTION_GROUPS: tuple[dict, ...] = (
    {"keys": ("id",),
     "question": "【ETL 建議檔】{subject} 的 ETL pipeline 識別碼（id）要用什麼？",
     "answer": "建議 `{derived_id}`（工具推導自主體名）；有既定命名規則請改成"
               "貴系統的 pipeline ID。"},
    {"keys": ("product_suite", "namespace"),
     "question": "【ETL 建議檔】{subject} 屬於哪個 product suite？"
                 "ETL 系統內要放在哪個 namespace？",
     "answer": "product suite：{product_hint}；namespace：{namespace_hint}。"
               "請確認或改成正確的值。"},
    {"keys": ("source_db", "target_db", "platform"),
     "question": "【ETL 建議檔】{subject} 的 ETL 來源 DB 與目標 DB 分別是什麼？"
                 "資料最終用在哪個 database（ex: clickhouse）？",
     "answer": "來源 DB：（請填來源系統的 database 名）；目標 DB：（請填寫入的 "
               "database 名）；使用的 database：{platform_hint}。"},
    {"keys": ("write_mode",),
     "question": "【ETL 建議檔】{subject} 各表的資料更新方式是什麼"
                 "（insert／deleteInsert／…）？",
     "answer": "建議 append-only 的事實表用 `insert`；需要可重跑覆寫的批次用 "
               "`deleteInsert`（先刪分區再寫入）。可用值：{write_modes}——"
               "逐表不同請一併說明。"},
    {"keys": ("schedule",),
     "question": "【ETL 建議檔】{subject} 的資料更新頻率是多少？",
     "answer": "建議 `daily 02:00`（每日離峰批次）；時效性需求較高改 `hourly`。"
               "逐表不同請一併說明。"},
    {"keys": ("cpu", "memory"),
     "question": "【ETL 建議檔】{subject} 的 ETL 任務需要多少 CPU／Memory 配置？",
     "answer": "建議先以 cpu `2`、memory `4Gi` 起跳，跑過一輪後依實際資料量調整。"},
    {"keys": ("owner",),
     "question": "【ETL 建議檔】{subject} 這條 ETL pipeline 的 owner"
                 "（負責人／團隊）是誰？",
     "answer": "（請填負責人或團隊，建議附可聯絡的信箱／群組）"},
)


def open_questions(subject: str, manifest: dict,
                   domains: list[str] | None = None) -> list[dict]:
    """缺（或工具自行推導）的欄位 → 設計提問（含代填的建議答案）。
    全部由設計稿宣告齊了就回空 list。

    格式同 design_result 的 open_questions，直接餵給
    `design.merge_design_answers` 寫進 design_answers.yaml。"""
    missing = set(manifest.get("needs_input")
                  or manifest.get("missing") or [])
    if not missing:
        return []
    pipeline = manifest["pipeline"]
    subs = {
        "subject": subject,
        "derived_id": pipeline["id"]["value"] or f"etl_{_slug(subject)}",
        "product_hint": (pipeline["product_suite"]["value"]
                         or "（請填產品線名稱）"),
        "namespace_hint": (pipeline["namespace"]["value"]
                           or (f"建議沿用 domain `{domains[0]}`（小寫）"
                               if domains else "（請填命名空間）")),
        "platform_hint": pipeline["platform"]["value"] or DEFAULT_PLATFORM,
        "write_modes": "、".join(f"`{m}`" for m in WRITE_MODES),
    }
    out = []
    for group in QUESTION_GROUPS:
        if not (missing & set(group["keys"])):
            continue
        out.append({"question": group["question"].format(**subs),
                    "proposed_answer": group["answer"].format(**subs)})
    return out


# ---------------------------------------------------------------- 報告呈現

def status_rows(manifest: dict) -> list[dict]:
    """pipeline 層欄位的填寫狀態（給設計報告呈現）。"""
    return [{"label": f["label"], "key": f["key"],
             "value": manifest["pipeline"][f["key"]]["value"],
             "origin": manifest["pipeline"][f["key"]]["origin"]}
            for f in PIPELINE_FIELDS]


def summary(manifest: dict) -> dict:
    """{filled, total, missing}——填了幾欄、還缺哪些（pipeline 層）。"""
    rows = status_rows(manifest)
    return {"total": len(rows),
            "filled": sum(1 for r in rows if r["origin"] != "missing"),
            "missing": [r["label"] for r in rows if r["origin"] == "missing"]}


def validate(result) -> list[str]:
    """驗證 design_result 的 etl_pipeline 區塊（選填；型別與表名一致性）。"""
    spec = result.get("etl_pipeline")
    if spec is None:
        return []
    if not isinstance(spec, dict):
        return ["etl_pipeline 必須是 object（ETL 建議檔的設定；可整段省略）"]
    errors: list[str] = []
    allowed = {f["key"] for f in PIPELINE_FIELDS
               if f["key"] not in RESOURCE_KEYS} | {"resources", "tables"}
    extra = sorted(set(spec) - allowed)
    if extra:
        errors.append(f"etl_pipeline 不允許的欄位：{extra}"
                      f"（可用：{sorted(allowed)}）")
    for key in sorted(set(spec) & allowed - {"resources", "tables"}):
        if not isinstance(spec[key], str):
            errors.append(f"etl_pipeline.{key} 必須是字串")
    errors += _resource_errors(spec.get("resources"), "etl_pipeline")
    tables = spec.get("tables")
    if tables is None:
        return errors
    if not isinstance(tables, list):
        return errors + ["etl_pipeline.tables 必須是 array（逐表覆寫設定）"]
    known = {str(t.get("name", "")).lower()
             for t in (result.get("physical_design") or {}).get("tables") or []
             if isinstance(t, dict)}
    table_allowed = set(TABLE_KEYS) - set(RESOURCE_KEYS) | {"table",
                                                            "resources"}
    for i, entry in enumerate(tables):
        if not isinstance(entry, dict) or not _clean(entry.get("table")):
            errors.append(f"etl_pipeline.tables[{i}] 必須含非空 table（表名）")
            continue
        name = _clean(entry["table"])
        if known and name.lower() not in known:
            errors.append(f"etl_pipeline.tables[{i}].table `{name}` 不存在於 "
                          "physical_design.tables——ETL job 的表名必須是設計"
                          "出來的表")
        extra = sorted(set(entry) - table_allowed)
        if extra:
            errors.append(f"etl_pipeline.tables[{i}] 不允許的欄位：{extra}")
        for key in sorted(set(entry) & table_allowed - {"resources"}):
            if not isinstance(entry[key], str):
                errors.append(f"etl_pipeline.tables[{i}].{key} 必須是字串")
        errors += _resource_errors(entry.get("resources"),
                                   f"etl_pipeline.tables[{i}]")
    return errors


def _resource_errors(resources, where: str) -> list[str]:
    if resources is None:
        return []
    if not isinstance(resources, dict):
        return [f"{where}.resources 必須是 object（cpu／memory）"]
    out = []
    extra = sorted(set(resources) - set(RESOURCE_KEYS))
    if extra:
        out.append(f"{where}.resources 不允許的欄位：{extra}")
    for key in sorted(set(resources) & set(RESOURCE_KEYS)):
        if not isinstance(resources[key], str):
            out.append(f"{where}.resources.{key} 必須是字串"
                       "（如 '2'、'4Gi'）")
    return out
