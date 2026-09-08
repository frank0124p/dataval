"""DataHub（中介資料平台）治理層 — v0.13.3。

govern mode 除了看 DDL 本身，還要看「這張表在中介資料平台上被治理成什麼樣」：
有沒有業務負責人、標籤打了沒、表與欄的描述寫了沒、血緣接上了沒、開出去的表
有沒有授權給該用的 AP、ETL 跑完有沒有資料品質檢查。

**架構分工（這是本模組唯一要記住的事）**

    datahub_fetch.py ──連網──> dataval/datahub_client.py
                                （API ready 時只改這裡）
                                        ↓
                          govern_doc/<名>/<名>.datahub.json（snapshot）

    run.py / merge_advisory.py ──零網路──> dataval/datahub.py ──> govern report
                                            （本模組：純函式）

run.py 不連網。它只讀 snapshot，把 snapshot 的事實換算成確定性 findings。
理由有三：報告要能位元組穩定重現、審計時要能回頭看「當時平台上是什麼樣」、
以及 API 還沒好的時候整條流程照跑（全部 skipped，不擋任何人）。

**七項檢查**（全在閘門區，零 LLM；描述「寫得對不對」是語意，那歸顧問區）

    DATAHUB.OWNER          業務負責人（biz owner）
    DATAHUB.TAG            必要標籤
    DATAHUB.TABLE_DESC     表描述
    DATAHUB.COLUMN_DESC    欄描述覆蓋率
    DATAHUB.LINEAGE        上游血緣
    DATAHUB.ACCESS_GRANT   授權給權限 AP        （自建 API）
    DATAHUB.QUALITY_CHECK  ETL 後資料品質檢查   （assertions 或自建 API）

**三態**：snapshot 沒有這個面向（API 未接／呼叫失敗）→ `skipped`，永不擋；
有資料且合格 → `pass`；有資料但不合格 → 依 `config/_engine/datahub.yaml`
的 `enforcement`（`off`／`warning`／`error`）。預設一律 `warning`——中介資料
治理是漸進的，不該一開機就把所有人擋在門外。
"""
from __future__ import annotations

import os

from .model import Finding, ZONE_GATING

#: snapshot 檔名後綴。放 govern_doc/<名>/——它是**機器產生的產物**，
#: 不是使用者權威輸入，所以不該混進 input/（那裡只放使用者自己寫的東西）。
SNAPSHOT_SUFFIX = ".datahub.json"
#: 引擎層設定檔（相對 config/）
CONFIG_REL = "_engine/datahub.yaml"
#: 每個 subject 可選填的「去平台哪裡拿」宣告（使用者權威輸入，放 input/）
TARGETS_NAME = "datahub.yaml"
#: 本整合對應的 DataHub 版本
DATAHUB_VERSION = "v0.13.3"
CATEGORY = "metadata"

#: 面向 key → (check_id, 中文標題)。順序＝報告呈現順序。
ASPECTS: tuple[tuple[str, str, str], ...] = (
    ("owner",         "DATAHUB.OWNER",         "業務負責人（biz owner）"),
    ("tag",           "DATAHUB.TAG",           "必要標籤"),
    ("table_desc",    "DATAHUB.TABLE_DESC",    "表描述"),
    ("column_desc",   "DATAHUB.COLUMN_DESC",   "欄描述覆蓋率"),
    ("lineage",       "DATAHUB.LINEAGE",       "上游血緣"),
    ("access_grant",  "DATAHUB.ACCESS_GRANT",  "權限 AP 授權"),
    ("quality_check", "DATAHUB.QUALITY_CHECK", "ETL 後資料品質檢查"),
)
ASPECT_KEYS = tuple(a[0] for a in ASPECTS)
CHECK_IDS = tuple(a[1] for a in ASPECTS)
_TITLE = {a[0]: a[2] for a in ASPECTS}
_CHECK_ID = {a[0]: a[1] for a in ASPECTS}

#: 哪些面向靠自建 API（報告會標明來源，讓人知道要找誰接）
SELF_HOSTED = {"access_grant", "quality_check"}

#: 預設設定。config/_engine/datahub.yaml 只覆寫要改的鍵。
DEFAULTS: dict = {
    "enabled": True,
    "version": DATAHUB_VERSION,
    "platform": "clickhouse",
    "env": "PROD",
    "container": "",              # DataHub URN 的 database／schema 前綴
    "server": "",                 # GMS base URL；空＝還沒接
    "ui_url": "",                 # DataHub 網頁版 base URL（報告的連結用）
    "grant_api": "",              # 自建授權 API base URL
    "quality_api": "",            # 自建資料品質 API base URL
    "required_tags": [],          # 每張表都要有的標籤（空＝只要有標籤就算過）
    "biz_owner_types": ["BUSINESS_OWNER", "BUSINESSOWNER", "DATAOWNER"],
    "column_desc_min_coverage": 0.9,
    "min_quality_checks": 1,
    "required_grant_aps": [],     # 一定要授權到的 AP（空＝有任一筆授權就算過）
    "enforcement": {key: "warning" for key in ASPECT_KEYS},
}

_LEVELS = ("off", "warning", "error")


# ------------------------------------------------------------------ 設定

def load_settings(config_dir: str = "config") -> dict:
    """讀 `config/_engine/datahub.yaml`，與 DEFAULTS 合併。壞檔不中斷驗證。"""
    settings = dict(DEFAULTS)
    settings["enforcement"] = dict(DEFAULTS["enforcement"])
    path = os.path.join(config_dir or "config", CONFIG_REL)
    if not os.path.isfile(path):
        return settings
    try:
        import yaml
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    except Exception:
        return settings
    if not isinstance(raw, dict):
        return settings
    enforcement = raw.pop("enforcement", None)
    settings.update({k: v for k, v in raw.items() if v is not None})
    if isinstance(enforcement, dict):
        for key, level in enforcement.items():
            level = _level(level)
            if key in ASPECT_KEYS and level:
                settings["enforcement"][key] = level
    return settings


def _level(value) -> str:
    """卡控強度正規化。YAML 1.1 把裸寫的 `off` 讀成布林 False——設定檔裡
    `tag: off` 是最自然的寫法，不能因為這個就靜默失效。"""
    if value is False:
        return "off"
    if value is True:
        return "warning"
    text = str(value or "").strip().lower()
    return text if text in _LEVELS else ""


def expand_env(value: str) -> str:
    """`${DATAHUB_GMS}` → 環境變數。設定檔不放 token，只放變數名。"""
    return os.path.expandvars(str(value or ""))


def dataset_urn(table: str, settings: dict, overrides: dict | None = None) -> str:
    """DataHub v0.13.3 的 dataset URN。fetch 與報告都用這個當唯一識別。

    `overrides` 是該表在 `input/<名>/datahub.yaml` 的宣告，逐段覆寫全域設定
    （平台上的表名跟 DDL 不同名、放在別的 container、跑在別的 env 都很常見）。"""
    over = overrides or {}
    platform = over.get("platform") or settings.get("platform", "clickhouse")
    env = over.get("env") or settings.get("env", "PROD")
    container = str(over.get("container")
                    if over.get("container") is not None
                    else settings.get("container") or "").strip(".")
    name = str(over.get("name") or table)
    full = f"{container}.{name}" if container else name
    return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{full},{env})"


# ------------------------------------------ 去平台哪裡拿（input 可宣告）

#: 每張表可宣告的鍵。除了 urn 是「整串直接指定」，其餘都是逐段覆寫。
TARGET_KEYS = ("urn", "name", "platform", "env", "container",
               "grant_key", "quality_key", "url")
#: 面向 → DataHub 網頁版的分頁（報告連結直接落在該看的那一頁）
ASPECT_TAB = {
    "owner": "", "tag": "", "table_desc": "Documentation",
    "column_desc": "Schema", "lineage": "Lineage",
    "access_grant": "", "quality_check": "Validation",
}


def targets_path(ddl_path: str) -> str:
    """`input/<名>/<名>.sql` → `input/<名>/datahub.yaml`。"""
    return os.path.join(os.path.dirname(os.path.abspath(ddl_path)),
                        TARGETS_NAME)


def load_targets(ddl_path: str) -> tuple[dict, list[str]]:
    """讀該 subject 的「去平台哪裡拿」宣告。回傳 (targets, problems)。

    選填件：沒有就回空的（表名怎麼推導見 dataset_urn）。壞檔只回問題描述，
    由呼叫端決定怎麼提醒——治理不因為一份選填設定壞掉就停擺。"""
    path = targets_path(ddl_path)
    if not os.path.isfile(path):
        return {}, []
    try:
        import yaml
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    except Exception as error:
        return {}, [f"{TARGETS_NAME} 無法解析：{type(error).__name__}: {error}"]
    if not isinstance(raw, dict):
        return {}, [f"{TARGETS_NAME} 根節點必須是 mapping"]
    problems: list[str] = []
    tables = raw.pop("tables", None) or {}
    if not isinstance(tables, dict):
        problems.append(f"{TARGETS_NAME} 的 tables 必須是「表名 → 設定」對照")
        tables = {}
    clean_tables: dict[str, dict] = {}
    for table, spec in tables.items():
        if not isinstance(spec, dict):
            problems.append(f"{TARGETS_NAME} 的 tables.{table} 必須是 mapping")
            continue
        unknown = [k for k in spec if k not in TARGET_KEYS]
        if unknown:
            problems.append(f"{TARGETS_NAME} 的 tables.{table} 有不認得的鍵："
                            + "、".join(unknown)
                            + f"；可用：{'、'.join(TARGET_KEYS)}")
        clean_tables[str(table).lower()] = {
            k: v for k, v in spec.items() if k in TARGET_KEYS}
    defaults = {k: v for k, v in raw.items()
                if k in ("platform", "env", "container", "ui_url")}
    unknown_top = [k for k in raw if k not in defaults]
    if unknown_top:
        problems.append(f"{TARGETS_NAME} 有不認得的頂層鍵："
                        + "、".join(unknown_top)
                        + "；可用：platform、env、container、ui_url、tables")
    return {"defaults": defaults, "tables": clean_tables}, problems


def resolve_target(table: str, settings: dict,
                   targets: dict | None = None) -> dict:
    """一張表要去平台哪裡拿。宣告 > subject 預設 > 全域設定 > 依表名推導。"""
    targets = targets or {}
    base = dict(settings)
    base.update({k: v for k, v in (targets.get("defaults") or {}).items()
                 if v is not None})
    over = (targets.get("tables") or {}).get(table.lower(), {})
    urn = str(over.get("urn") or "").strip()
    declared = bool(over)
    if not urn:
        urn = dataset_urn(table, base, over)
    ui = str(over.get("url") or base.get("ui_url") or "").rstrip("/")
    return {
        "table": table,
        "urn": urn,
        "declared": declared,
        "origin": ("input/<名>/datahub.yaml 宣告" if declared
                   else "依表名與 config/_engine/datahub.yaml 推導"),
        "ui_url": ui,
        "link": f"{ui}/dataset/{urn}" if ui else "",
        # 自建 API 的識別碼未必是 URN；沒宣告就退回用 URN
        "grant_key": str(over.get("grant_key") or urn),
        "quality_key": str(over.get("quality_key") or urn),
    }


def resolve_targets(tables: list[str], settings: dict,
                    targets: dict | None = None) -> dict[str, dict]:
    return {t: resolve_target(t, settings, targets) for t in sorted(tables)}


def aspect_link(target: dict, aspect: str) -> str:
    """該面向在 DataHub 網頁版的位置（沒設 ui_url 就沒有連結）。"""
    if not target.get("link"):
        return ""
    tab = ASPECT_TAB.get(aspect, "")
    return target["link"] + (f"/{tab}" if tab else "")


# ------------------------------------------------------------- snapshot

def snapshot_path(doc_root: str, subject: str, create: bool = False) -> str:
    """snapshot 的家：`govern_doc/<名>/<名>.datahub.json`。"""
    from . import docpaths
    return os.path.join(docpaths.govern_dir(doc_root, subject, create=create),
                        subject + SNAPSHOT_SUFFIX)


def empty_snapshot(reason: str = "尚未抓取") -> dict:
    """沒有 snapshot 時的空殼——所有面向都 unavailable，全部 skipped。"""
    return {"schema_version": 1, "source": "none", "reason": reason,
            "fetched_at": "", "server": "", "datasets": {},
            "unavailable": list(ASPECT_KEYS)}


def load_snapshot(doc_root: str, subject: str) -> dict:
    """讀 snapshot；沒有或壞掉都回空殼（缺 API 不該讓治理停擺）。"""
    path = snapshot_path(doc_root, subject)
    if not os.path.isfile(path):
        return empty_snapshot("尚未抓取 snapshot；執行 python datahub_fetch.py")
    try:
        import json
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as error:
        return empty_snapshot(f"snapshot 無法讀取：{error}")
    if not isinstance(data, dict) or not isinstance(data.get("datasets"), dict):
        return empty_snapshot("snapshot 格式不符（缺 datasets）")
    data.setdefault("unavailable", [])
    data.setdefault("source", "unknown")
    return data


def validate_snapshot(data: dict) -> list[str]:
    """snapshot 契約檢查。回傳問題描述（空＝合格）。fetch 端與測試共用。"""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["snapshot 必須是物件"]
    if not isinstance(data.get("datasets"), dict):
        problems.append("缺 `datasets`（表名 → 該表的中介資料）")
    for key in data.get("unavailable") or []:
        if key not in ASPECT_KEYS:
            problems.append(f"unavailable 出現未知面向 `{key}`；"
                            f"可用：{'、'.join(ASPECT_KEYS)}")
    for table, entry in (data.get("datasets") or {}).items():
        if not isinstance(entry, dict):
            problems.append(f"datasets.{table} 必須是物件")
            continue
        for field, kind in (("owners", list), ("tags", list),
                            ("columns", dict), ("access_grants", list),
                            ("quality_checks", list)):
            if field in entry and not isinstance(entry[field], kind):
                problems.append(f"datasets.{table}.{field} 型別不符"
                                f"（應為 {kind.__name__}）")
    return problems


# ------------------------------------------------------- 七項面向的判定
# 每個 evaluator 都是純函式：(表的 snapshot 條目, 設定) → (合格?, 實際情形, 佐證)
# 只判定「有沒有」這種確定性事實。「寫得對不對」是語意，那是顧問區的事。

def _eval_owner(entry: dict, settings: dict):
    wanted = {str(t).upper().replace("_", "")
              for t in settings.get("biz_owner_types") or []}
    owners = [o for o in entry.get("owners") or [] if isinstance(o, dict)]
    biz = [o for o in owners
           if str(o.get("type", "")).upper().replace("_", "") in wanted]
    names = [str(o.get("name") or o.get("urn") or "?") for o in biz]
    if biz:
        return True, "業務負責人：" + "、".join(names), biz
    if owners:
        other = "、".join(f"{o.get('name') or o.get('urn')}"
                          f"（{o.get('type', '?')}）" for o in owners)
        return False, f"只有非業務類型的 owner：{other}", owners
    return False, "平台上沒有登錄任何 owner", []


def _eval_tag(entry: dict, settings: dict):
    tags = [str(t) for t in entry.get("tags") or []]
    required = [str(t) for t in settings.get("required_tags") or []]
    missing = [t for t in required if t not in tags]
    if missing:
        return (False, f"缺必要標籤：{'、'.join(missing)}"
                + (f"；已有：{'、'.join(tags)}" if tags else "（一個標籤都沒有）"),
                {"tags": tags, "missing": missing})
    if not tags and not required:
        return False, "平台上沒有任何標籤", {"tags": []}
    return True, "標籤：" + "、".join(tags), {"tags": tags}


def _eval_table_desc(entry: dict, settings: dict):
    desc = " ".join(str(entry.get("description") or "").split())
    if not desc:
        return False, "平台上沒有表描述", ""
    if len(desc) < 8:
        return False, f"表描述過短（{len(desc)} 字）：「{desc}」", desc
    return True, f"表描述：「{desc[:60]}{'…' if len(desc) > 60 else ''}」", desc


def _eval_column_desc(entry: dict, settings: dict):
    columns = entry.get("columns") or {}
    if not columns:
        return False, "平台上沒有任何欄位中介資料", {"total": 0}
    missing = sorted(name for name, col in columns.items()
                     if not str((col or {}).get("description") or "").strip())
    total = len(columns)
    covered = total - len(missing)
    ratio = covered / total if total else 0.0
    floor = float(settings.get("column_desc_min_coverage") or 0)
    evidence = {"total": total, "covered": covered, "missing": missing,
                "coverage": round(ratio, 4)}
    shown = "、".join(f"`{m}`" for m in missing[:12]) + \
        ("…" if len(missing) > 12 else "")
    if ratio + 1e-9 < floor:
        return (False, f"欄描述覆蓋 {covered}/{total}（{ratio:.0%}），"
                f"低於門檻 {floor:.0%}；缺：{shown}", evidence)
    return True, f"欄描述覆蓋 {covered}/{total}（{ratio:.0%}）" + \
        (f"；仍缺：{shown}" if missing else ""), evidence


def _eval_lineage(entry: dict, settings: dict):
    lineage = entry.get("lineage") or {}
    up = [str(u) for u in lineage.get("upstreams") or []]
    down = [str(d) for d in lineage.get("downstreams") or []]
    if up:
        return (True, f"上游 {len(up)} 條"
                + (f"、下游 {len(down)} 條" if down else ""),
                {"upstreams": up, "downstreams": down})
    return (False, "平台上沒有上游血緣"
            + (f"（有下游 {len(down)} 條）" if down else ""),
            {"upstreams": [], "downstreams": down})


def _eval_access_grant(entry: dict, settings: dict):
    grants = [g for g in entry.get("access_grants") or [] if isinstance(g, dict)]
    granted = [g for g in grants if g.get("granted", True)]
    required = [str(a) for a in settings.get("required_grant_aps") or []]
    have = {str(g.get("ap") or g.get("principal") or "") for g in granted}
    missing = [a for a in required if a not in have]
    listing = "、".join(f"{g.get('ap') or g.get('principal')}"
                       f"（{g.get('level', 'read')}）" for g in granted)
    if missing:
        return (False, f"未授權給：{'、'.join(missing)}"
                + (f"；已授權：{listing}" if listing else "（目前無任何授權）"),
                {"granted": granted, "missing": missing})
    if not granted:
        return False, "這張表沒有授權給任何權限 AP", {"granted": []}
    return True, f"已授權：{listing}", {"granted": granted}


def _eval_quality_check(entry: dict, settings: dict):
    checks = [c for c in entry.get("quality_checks") or [] if isinstance(c, dict)]
    minimum = int(settings.get("min_quality_checks") or 1)
    if len(checks) < minimum:
        return (False, f"ETL 後只有 {len(checks)} 項資料品質檢查"
                f"（要求至少 {minimum} 項）", {"checks": checks})
    failed = [c for c in checks
              if str(c.get("status", "")).upper() in ("FAIL", "FAILURE", "ERROR")]
    never = [c for c in checks if not c.get("last_run")]
    if failed:
        return (False, f"{len(checks)} 項檢查中有 {len(failed)} 項最近一次是失敗："
                + "、".join(f"`{c.get('name', '?')}`" for c in failed),
                {"checks": checks, "failed": failed})
    if never:
        return (False, f"{len(checks)} 項檢查中有 {len(never)} 項從未執行："
                + "、".join(f"`{c.get('name', '?')}`" for c in never),
                {"checks": checks, "never_run": never})
    return (True, f"{len(checks)} 項資料品質檢查皆通過："
            + "、".join(f"`{c.get('name', '?')}`" for c in checks),
            {"checks": checks})


_EVALUATORS = {
    "owner": _eval_owner, "tag": _eval_tag, "table_desc": _eval_table_desc,
    "column_desc": _eval_column_desc, "lineage": _eval_lineage,
    "access_grant": _eval_access_grant, "quality_check": _eval_quality_check,
}

#: 每個面向的「為什麼要管」與「怎麼修」——報告的四問之二與之四。
_RATIONALE = {
    "owner": "沒有業務負責人的表，出事時沒有人能決定「這個值到底該是什麼」；"
             "技術 owner 只能答怎麼跑，不能答對不對。",
    "tag": "標籤是平台上唯一能被搜尋與被政策引用的分類（分級、PII、保存期限）；"
           "沒打標籤等於下游治理政策管不到這張表。",
    "table_desc": "表描述是消費者看到的第一句話；沒有描述的表在平台上等同黑箱，"
                  "只能靠問人，知識不會沉澱。",
    "column_desc": "欄位描述是資料字典的最小單位，平台直接讀它；"
                   "沒有描述的欄位對下游是黑箱，也是重複造欄的起點。",
    "lineage": "沒有血緣就沒有影響分析：上游改一個欄位，沒人知道會炸到誰。",
    "access_grant": "表開出來是為了被用；沒有授權給該用的 AP，等於做完沒交付，"
                    "而且事後補授權往往繞過既有的權限審核。",
    "quality_check": "ETL 跑完沒有品質檢查，錯誤資料會安靜地流到下游；"
                     "壞資料比沒有資料更貴。",
}
_FIX = {
    "owner": "在 DataHub 該 dataset 的 Owners 加上業務負責人（type 選 "
             "Business Owner），再重跑 python datahub_fetch.py。",
    "tag": "在 DataHub 該 dataset 補上必要標籤（清單見 "
           "config/_engine/datahub.yaml 的 required_tags）後重抓 snapshot。",
    "table_desc": "在 DataHub 補 dataset description，或在 DDL 的表註解寫清楚"
                  "再讓 ingestion 帶上去。",
    "column_desc": "補齊缺描述的欄位（DDL 的 COMMENT 或平台上直接編輯），"
                   "再重抓 snapshot。",
    "lineage": "確認 ETL 有送出 lineage（或在平台手動補 upstream）；"
               "本 repo 的 input/<名>/relations.yaml 可作為宣告依據。",
    "access_grant": "透過權限系統把這張表授權給該用的 AP；"
                    "必要 AP 清單見 config/_engine/datahub.yaml 的 "
                    "required_grant_aps。",
    "quality_check": "在 ETL 之後掛上資料品質檢查（DataHub assertions 或自建"
                     "檢查），並確認最近一次有實際執行且通過。",
}
_EXPECTED = {
    "owner": "平台上登錄業務負責人（biz owner）",
    "tag": "平台上具備必要標籤",
    "table_desc": "平台上有表描述",
    "column_desc": "欄描述覆蓋率達設定門檻",
    "lineage": "平台上有上游血緣",
    "access_grant": "已授權給該用的權限 AP",
    "quality_check": "ETL 後有資料品質檢查且最近一次通過",
}


# ------------------------------------------------------ 平台上的「值」
# 判定看的是「合不合格」，報告還要回答「平台上到底填了什麼」——那是兩件事。
# 這裡把每個面向的值本身抽出來（短、可直接放進表格），沒有就回 NO_VALUE。

NO_VALUE = "（無）"


def _clip(text: str, limit: int = 48) -> str:
    text = " ".join(str(text or "").split())
    return text[:limit] + ("…" if len(text) > limit else "")


def _value_owner(entry, settings):
    wanted = {str(t).upper().replace("_", "")
              for t in settings.get("biz_owner_types") or []}
    names = [str(o.get("name") or o.get("urn") or "?")
             for o in entry.get("owners") or [] if isinstance(o, dict)
             and str(o.get("type", "")).upper().replace("_", "") in wanted]
    return "、".join(names) or NO_VALUE


def _value_tag(entry, settings):
    return "、".join(str(t) for t in entry.get("tags") or []) or NO_VALUE


def _value_table_desc(entry, settings):
    return _clip(entry.get("description")) or NO_VALUE


def _value_column_desc(entry, settings):
    columns = entry.get("columns") or {}
    if not columns:
        return NO_VALUE
    covered = sum(1 for c in columns.values()
                  if str((c or {}).get("description") or "").strip())
    return f"{covered}/{len(columns)}（{covered / len(columns):.0%}）"


def _value_lineage(entry, settings):
    ups = (entry.get("lineage") or {}).get("upstreams") or []
    return f"上游 {len(ups)} 條" if ups else NO_VALUE


def _value_access_grant(entry, settings):
    grants = [g for g in entry.get("access_grants") or []
              if isinstance(g, dict) and g.get("granted", True)]
    return "、".join(f"{g.get('ap') or g.get('principal')}"
                     f"（{g.get('level', 'read')}）"
                     for g in grants) or NO_VALUE


def _value_quality_check(entry, settings):
    checks = [c for c in entry.get("quality_checks") or [] if isinstance(c, dict)]
    if not checks:
        return NO_VALUE
    icon = {"PASS": "✅", "FAIL": "❌", "FAILURE": "❌", "ERROR": "❌"}
    return _clip("、".join(
        f"{c.get('name', '?')}{icon.get(str(c.get('status', '')).upper(), '⏳')}"
        for c in checks))


_VALUES = {
    "owner": _value_owner, "tag": _value_tag, "table_desc": _value_table_desc,
    "column_desc": _value_column_desc, "lineage": _value_lineage,
    "access_grant": _value_access_grant, "quality_check": _value_quality_check,
}


def platform_value(aspect: str, entry: dict, settings: dict) -> str:
    """平台上這個面向填了什麼。抓不到／沒填一律回 NO_VALUE。"""
    try:
        return _VALUES[aspect](entry or {}, settings) or NO_VALUE
    except Exception:
        return NO_VALUE


# ------------------------------------------------------------ 閘門區檢查

def _skip(aspect: str, target: str, reason: str) -> Finding:
    check_id = _CHECK_ID[aspect]
    source = "自建 API" if aspect in SELF_HOSTED else f"DataHub {DATAHUB_VERSION} API"
    return Finding(
        check_id, CATEGORY, "skipped", target,
        f"{_TITLE[aspect]}：尚未檢查（{reason}）。此面向的資料由「{source}」"
        "提供，接上後本項會自動變成實檢結果。",
        rationale=_RATIONALE[aspect], expected=_EXPECTED[aspect],
        actual=f"沒有可判定的中介資料（{reason}）",
        fix="執行 python datahub_fetch.py 產生 "
            "govern_doc/<名>/<名>.datahub.json；"
            "API 未接時見 config/_engine/datahub.yaml。",
        severity="info", source="rule", zone=ZONE_GATING,
        evidence={"aspect": aspect, "state": "unavailable", "reason": reason})


def evaluate(schema, snapshot: dict, settings: dict) -> list[dict]:
    """把 snapshot 換算成每表每面向的判定結果（純資料，給 findings 與報告共用）。

    回傳 [{table, aspect, check_id, title, state, ok, actual, level, evidence}]，
    state ∈ unavailable｜pass｜violation｜off。順序固定（表名 × ASPECTS）。"""
    rows: list[dict] = []
    unavailable = set(snapshot.get("unavailable") or [])
    datasets = snapshot.get("datasets") or {}
    lowered = {str(k).lower(): v for k, v in datasets.items()}
    for table in [t.name for t in getattr(schema, "tables", []) or []]:
        entry = lowered.get(table.lower())
        for aspect in ASPECT_KEYS:
            level = str(settings.get("enforcement", {}).get(aspect, "warning"))
            base = {"table": table, "aspect": aspect,
                    "check_id": _CHECK_ID[aspect], "title": _TITLE[aspect],
                    "level": level,
                    "self_hosted": aspect in SELF_HOSTED}
            if level == "off":
                rows.append({**base, "state": "off", "ok": None,
                             "actual": "已在 config 關閉此項", "evidence": None,
                             "value": "—"})
                continue
            if aspect in unavailable:
                rows.append({**base, "state": "unavailable", "ok": None,
                             "actual": snapshot.get("reason")
                             or "API 尚未提供此面向", "evidence": None,
                             "value": "—"})
                continue
            if entry is None:
                rows.append({**base, "state": "unavailable", "ok": None,
                             "actual": "平台上找不到這張表（snapshot 無此 dataset）",
                             "evidence": None, "value": "—"})
                continue
            ok, actual, evidence = _EVALUATORS[aspect](entry, settings)
            rows.append({**base, "state": "pass" if ok else "violation",
                         "ok": ok, "actual": actual, "evidence": evidence,
                         "value": platform_value(aspect, entry, settings)})
    return rows


def run(schema, config_dir: str = "config",
        snapshot: dict | None = None, targets: dict | None = None,
        target_problems: list[str] | None = None) -> tuple[list[Finding], dict]:
    """閘門區確定性檢查（零網路）。回傳 (findings, meta)。

    `enabled: false`、或 schema 沒有表 → 完全不作用（不該煩還沒接平台的人）。"""
    settings = load_settings(config_dir)
    if not settings.get("enabled", True):
        return [], {}
    tables = [t.name for t in getattr(schema, "tables", []) or []]
    if not tables:
        return [], {}
    if snapshot is None:
        snapshot = empty_snapshot()
    rows = evaluate(schema, snapshot, settings)
    resolved = resolve_targets(tables, settings, targets)

    findings: list[Finding] = []
    for problem in target_problems or []:
        # 選填設定壞掉 → 警告放行（照樣用推導的位置去找），但不能靜默
        findings.append(Finding(
            "SYSTEM.CONFIG_SPEC", CATEGORY, "warning", TARGETS_NAME,
            f"DataHub 查詢位置宣告無法使用（已改用推導的位置）：{problem}",
            severity="warning", source="rule", zone=ZONE_GATING,
            expected=f"input/<名>/{TARGETS_NAME} 可解析且鍵名正確",
            actual=problem,
            fix=f"修正 input/<名>/{TARGETS_NAME}；"
                "整份刪掉也可以——位置會依表名自動推導。"))
    # 沒抓到時每個面向只出一筆（每張表重複同一句話只是噪音；
    # 真的有資料要判定時才逐表出，因為那時每張表的實際情形不同）
    skipped_aspects: dict[str, str] = {}
    for row in rows:
        if row["state"] == "unavailable":
            skipped_aspects.setdefault(row["aspect"], row["actual"])
    for aspect, reason in skipped_aspects.items():
        findings.append(_skip(aspect, "(schema)", reason))
    for row in rows:
        aspect, table = row["aspect"], row["table"]
        if row["state"] in ("off", "unavailable"):
            continue
        source = ("自建 API" if row["self_hosted"]
                  else f"DataHub {DATAHUB_VERSION}")
        if row["ok"]:
            findings.append(Finding(
                row["check_id"], CATEGORY, "pass", table,
                f"{row['title']}：{row['actual']}。",
                rationale=_RATIONALE[aspect], expected=_EXPECTED[aspect],
                actual=row["actual"], severity="info", source="rule",
                zone=ZONE_GATING,
                evidence={"aspect": aspect, "state": "pass",
                          "detail": row["evidence"], "provider": source}))
            continue
        blocking = row["level"] == "error"
        findings.append(Finding(
            row["check_id"], CATEGORY, "fail" if blocking else "warning", table,
            f"{row['title']}：{row['actual']}。",
            rationale=_RATIONALE[aspect], expected=_EXPECTED[aspect],
            actual=row["actual"], fix=_FIX[aspect],
            severity="error" if blocking else "warning",
            source="rule", zone=ZONE_GATING,
            evidence={"aspect": aspect, "state": "violation",
                      "detail": row["evidence"], "provider": source}))
    return findings, report_meta(snapshot, settings, rows, resolved)


# ----------------------------------------------------------- 報告用 meta

def report_meta(snapshot: dict, settings: dict, rows: list[dict],
                targets: dict | None = None) -> dict:
    """govern report 的「DataHub 中介資料」區塊資料（md／html／json 共用）。"""
    counts = {"pass": 0, "violation": 0, "unavailable": 0, "off": 0}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    per_aspect = []
    for aspect, check_id, title in ASPECTS:
        subset = [r for r in rows if r["aspect"] == aspect]
        state = "off" if all(r["state"] == "off" for r in subset) and subset \
            else ("unavailable" if all(r["state"] in ("unavailable", "off")
                                       for r in subset) and subset
                  else ("violation" if any(r["state"] == "violation"
                                           for r in subset) else "pass"))
        detail = ([] if state in ("unavailable", "off")
                  else [{"table": r["table"], "state": r["state"],
                         "actual": r["actual"],
                         "value": r.get("value", "—"),
                         "link": aspect_link((targets or {}).get(r["table"], {}),
                                             aspect)}
                        for r in subset])
        per_aspect.append({
            "aspect": aspect, "check_id": check_id, "title": title,
            "state": state,
            "reason": (subset[0]["actual"] if subset and not detail else ""),
            "provider": "自建 API" if aspect in SELF_HOSTED
                        else f"DataHub {DATAHUB_VERSION}",
            "enforcement": settings.get("enforcement", {}).get(aspect, "warning"),
            "tables": detail,
        })
    return {
        "version": settings.get("version", DATAHUB_VERSION),
        "enabled": bool(settings.get("enabled", True)),
        "source": snapshot.get("source", "none"),
        "fetched_at": snapshot.get("fetched_at", ""),
        "server": snapshot.get("server", ""),
        "reason": snapshot.get("reason", ""),
        "connected": snapshot.get("source") not in (None, "", "none"),
        "datasets": sorted(snapshot.get("datasets") or {}),
        "unavailable": sorted(snapshot.get("unavailable") or []),
        "counts": counts,
        "aspects": per_aspect,
        "rows": rows,
        # 這次去平台的哪裡找（宣告的還是推導的），以及網頁版連結
        "targets": [targets[t] for t in sorted(targets or {})],
        "ui_url": str(settings.get("ui_url") or ""),
        "declared_targets": sum(1 for t in (targets or {}).values()
                                if t.get("declared")),
    }


def console_lines(meta: dict) -> list[str]:
    """run.py 的一行摘要。"""
    if not meta:
        return []
    counts = meta.get("counts") or {}
    if not meta.get("connected"):
        return [f"🏷 DataHub {meta.get('version', DATAHUB_VERSION)}："
                f"未接 API（{meta.get('reason') or '尚未抓取'}）"
                f"——7 項中介資料檢查全部 skipped，不影響合規判定"]
    bits = (f"通過 {counts.get('pass', 0)}、"
            f"未達標 {counts.get('violation', 0)}、"
            f"待接 {counts.get('unavailable', 0)}")
    return [f"🏷 DataHub {meta.get('version', DATAHUB_VERSION)}"
            f"（{meta.get('source')}）：{bits}"]


def advisory_material(meta: dict) -> str:
    """顧問區 prompt 素材：閘門只判「有沒有」，語意判「寫得對不對」。"""
    if not meta or not meta.get("connected"):
        return "（DataHub API 尚未接上——本次沒有平台中介資料可判讀）"
    lines = [f"**平台**：DataHub {meta.get('version')}"
             f"（snapshot {meta.get('fetched_at') or '—'}）", ""]
    lines += ["| 面向 | 狀態 | 實際情形 |", "|---|---|---|"]
    label = {"pass": "✅ 有", "violation": "⚠️ 缺", "unavailable": "⏭ 待接",
             "off": "— 關閉"}
    for aspect in meta.get("aspects") or []:
        detail = "；".join(f"`{t['table']}` {t['actual']}"
                          for t in aspect["tables"][:4]) or "—"
        lines.append(f"| {aspect['title']} | {label.get(aspect['state'], '')} "
                     f"| {detail.replace('|', '/')} |")
    lines += ["", "閘門區只判「有沒有」。請你判**內容對不對**：描述是否真的說明了"
              "這張表／這個欄位承載什麼事實（而不是把欄名重寫一次）、標籤的分級"
              "是否與資料敏感度相稱、血緣的上游是否就是 relations.yaml 宣告的那些、"
              "品質檢查是否檢在關鍵欄位上。"]
    return "\n".join(lines)
