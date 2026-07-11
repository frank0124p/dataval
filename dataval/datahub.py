"""DataHub station. First version = required-field (必填) checks only.

Modes:
  - bypass: DataHub not ready. Emits one advisory note, never blocks. (MVP default)
  - live:   query DataHub for each table/column and check required fields exist.

Conditional gate: if DataHub is configured but unreachable, the station DEGRADES
to advisory (info) and passes — preserving 'runs unattended'. The report records
whether this run was a real check or a degraded bypass.

Consistency / lineage cross-checks are intentionally deferred (future phase).
"""
from __future__ import annotations
import os
from .model import Schema, Finding, ZONE_GATING, ZONE_ADVISORY

# Required metadata fields expected on DataHub (configurable later).
REQUIRED_FIELDS = ["description", "subject_description"]


def _status_note(state: str, detail: str = "") -> Finding:
    msg = {
        "bypass": "DataHub 尚未接上，本站略過（bypass）。必填檢查未執行。",
        "degraded": "DataHub 設定了但連不上，本站降級為提示並放行。",
        "live": "DataHub 必填檢查已實際執行。",
    }[state]
    if detail:
        msg += f" 診斷：{detail}"
    return Finding(
        check_id="DATAHUB.STATION_STATE", category="datahub",
        status="info" if state == "live" else "skipped",
        target="(datahub)", message=msg,
        severity="info", source="rule",
        zone=ZONE_ADVISORY if state != "live" else ZONE_GATING)


def run(schema: Schema, cfg: dict) -> tuple[list[Finding], str]:
    """Returns (findings, state) where state in {bypass, degraded, live}."""
    dh = cfg.get("datahub", {})
    base_url = (dh.get("base_url") or os.environ.get("DATAVAL_DATAHUB_URL", "")).strip()

    # MVP: DataHub not ready -> bypass.
    if not dh.get("enabled", False) or not base_url:
        return [_status_note("bypass")], "bypass"

    # live path (kept simple; degrade on any error)
    try:
        metadata = _fetch_metadata(base_url, schema)  # may raise
    except Exception as e:
        return [_status_note("degraded", f"{type(e).__name__}: {e}")], "degraded"

    out = [_status_note("live")]
    required = dh.get("required_fields", REQUIRED_FIELDS)
    for t in schema.tables:
        entry = metadata.get(t.name)
        if entry is None:
            out.append(Finding("DATAHUB.ASSET_PRESENT", "datahub", "fail",
                               t.name, "DataHub 上找不到此表的條目。",
                               rationale="資產須登錄於 DataHub。",
                               source="rule", zone=ZONE_GATING))
            continue
        for fld in required:
            if not entry.get(fld):
                out.append(Finding("DATAHUB.REQUIRED_FIELD", "datahub", "fail",
                                   t.name, f"DataHub 必填欄位 '{fld}' 未填寫。",
                                   rationale="必填中介資料缺漏。",
                                   source="rule", zone=ZONE_GATING))
    return out, "live"


def _fetch_metadata(base_url: str, schema: Schema) -> dict:
    """Placeholder for the real DataHub query. Raise to trigger degrade.
    Wire this to your DataHub GraphQL/REST when ready."""
    raise NotImplementedError("DataHub integration not wired yet.")
