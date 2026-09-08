"""DataHub／自建 API 的**唯一連網層** — v0.13.3。

這是整包裡唯一會發網路請求的檔案。API ready 時要改的也只有這裡：
每個面向都拆成 `endpoint`（打哪支）＋ `parse`（回傳長什麼樣 → snapshot 欄位）
兩半，接上真 API 時把對應的 `_ENDPOINTS` 路徑與 `_PARSERS` 解析改對就好，
下游（檢查、報告、HTML、顧問區 prompt）完全不用動。

三種 client：

  NullClient     沒設定 server → 什麼都不抓，snapshot 標成全部 unavailable。
                 這是預設值，也是 API 沒好之前的狀態：整條流程照跑、不擋人。
  FixtureClient  讀本地 JSON（`DATAHUB_FIXTURE` 或 config 的 fixture 路徑）。
                 讓框架現在就能整條跑通、讓測試有確定性輸入。
  HttpClient     真連 DataHub GMS 與自建 API。骨架已經寫好，
                 `_request()` 與各 parser 是待接的縫。

抓完寫成 snapshot（`govern_doc/<名>/<名>.datahub.json`），之後 run.py 只讀那份檔案。
連網與判定分家，是為了讓 govern report 能位元組穩定重現，也讓審計能回頭看
「當時平台上到底是什麼樣」。
"""
from __future__ import annotations

import json
import os

from . import datahub

#: 每個面向要打哪支 API。`{urn}` 會被替換成 dataset URN。
#: --- API ready 時改這裡（路徑對了，下游就都對了）---------------------------
_ENDPOINTS: dict[str, dict] = {
    # DataHub v0.13.3 OpenAPI v2：/openapi/v2/entity/dataset/{urn}/{aspect}
    "owner":         {"api": "datahub", "aspect": "ownership",
                      "path": "/openapi/v2/entity/dataset/{urn}/ownership"},
    "tag":           {"api": "datahub", "aspect": "globalTags",
                      "path": "/openapi/v2/entity/dataset/{urn}/globalTags"},
    "table_desc":    {"api": "datahub", "aspect": "datasetProperties",
                      "path": "/openapi/v2/entity/dataset/{urn}/datasetProperties"},
    "column_desc":   {"api": "datahub", "aspect": "schemaMetadata",
                      "path": "/openapi/v2/entity/dataset/{urn}/schemaMetadata"},
    "lineage":       {"api": "datahub", "aspect": "upstreamLineage",
                      "path": "/openapi/v2/entity/dataset/{urn}/upstreamLineage"},
    # 自建 API（尚未提供；路徑先擺著，接上時改這兩行即可）。
    # `{key}` 是 input/<名>/datahub.yaml 的 grant_key／quality_key——
    # 自建系統的識別碼未必是 URN，沒宣告時退回用 URN。
    "access_grant":  {"api": "grant", "aspect": "grants",
                      "path": "/api/v1/datasets/{key}/grants"},
    "quality_check": {"api": "quality", "aspect": "assertions",
                      "path": "/api/v1/datasets/{key}/quality-checks"},
}

#: 面向 → 該面向的資料要落在 snapshot 的哪個欄位
_SNAPSHOT_FIELD = {
    "owner": "owners", "tag": "tags", "table_desc": "description",
    "column_desc": "columns", "lineage": "lineage",
    "access_grant": "access_grants", "quality_check": "quality_checks",
}

#: 面向 → 該面向要用哪個 base URL 設定鍵
_BASE_KEY = {"datahub": "server", "grant": "grant_api", "quality": "quality_api"}


# ---------------------------------------------------- 回傳 → snapshot 欄位
# --- API ready 時改這裡（真實 payload 的形狀對上 snapshot 契約）-------------

def _parse_owner(payload: dict) -> list[dict]:
    """`ownership` aspect → [{urn, type, name}]。"""
    owners = []
    for item in (payload or {}).get("owners") or []:
        urn = str(item.get("owner") or item.get("urn") or "")
        owners.append({
            "urn": urn,
            "type": str(item.get("type") or
                        (item.get("ownershipType") or {}).get("urn", "")
                        ).rsplit(":", 1)[-1],
            "name": item.get("name") or urn.rsplit(":", 1)[-1],
        })
    return owners


def _parse_tag(payload: dict) -> list[str]:
    """`globalTags` aspect → ["PII", "layer:DWD"]。"""
    out = []
    for item in (payload or {}).get("tags") or []:
        urn = str(item.get("tag") or item.get("urn") or item)
        out.append(urn.rsplit(":", 1)[-1] if urn.startswith("urn:") else urn)
    return out


def _parse_table_desc(payload: dict) -> str:
    """`datasetProperties`／`editableDatasetProperties` → 描述字串。"""
    return str((payload or {}).get("description") or "")


def _parse_column_desc(payload: dict) -> dict:
    """`schemaMetadata` → {欄名: {description, type}}。"""
    columns = {}
    for field in (payload or {}).get("fields") or []:
        name = str(field.get("fieldPath") or field.get("name") or "")
        if not name:
            continue
        columns[name.rsplit(".", 1)[-1]] = {
            "description": str(field.get("description") or ""),
            "type": str(field.get("nativeDataType") or ""),
        }
    return columns


def _parse_lineage(payload: dict) -> dict:
    """`upstreamLineage` → {upstreams: [urn], downstreams: [urn]}。"""
    ups = [str(u.get("dataset") or u.get("urn") or u)
           for u in (payload or {}).get("upstreams") or []]
    downs = [str(d.get("dataset") or d.get("urn") or d)
             for d in (payload or {}).get("downstreams") or []]
    return {"upstreams": ups, "downstreams": downs}


def _parse_access_grant(payload: dict) -> list[dict]:
    """自建授權 API → [{ap, principal, level, granted, ticket}]。"""
    out = []
    for item in (payload or {}).get("grants") or []:
        out.append({
            "ap": str(item.get("ap") or item.get("application") or ""),
            "principal": str(item.get("principal") or item.get("account") or ""),
            "level": str(item.get("level") or item.get("permission") or "read"),
            "granted": bool(item.get("granted", True)),
            "ticket": str(item.get("ticket") or ""),
        })
    return out


def _parse_quality_check(payload: dict) -> list[dict]:
    """自建品質 API（或 DataHub assertions）→ [{name, type, last_run, status}]。"""
    out = []
    items = (payload or {}).get("checks") or (payload or {}).get("assertions") or []
    for item in items:
        out.append({
            "name": str(item.get("name") or item.get("assertionUrn") or ""),
            "type": str(item.get("type") or item.get("scope") or ""),
            "column": str(item.get("column") or ""),
            "last_run": str(item.get("last_run") or item.get("lastEvaluatedAt") or ""),
            "status": str(item.get("status") or item.get("result") or "").upper(),
        })
    return out


_PARSERS = {
    "owner": _parse_owner, "tag": _parse_tag, "table_desc": _parse_table_desc,
    "column_desc": _parse_column_desc, "lineage": _parse_lineage,
    "access_grant": _parse_access_grant, "quality_check": _parse_quality_check,
}


# ------------------------------------------------------------------ client

class Client:
    """抓取契約。子類只要能回答「某表某面向的原始 payload 是什麼」。"""

    name = "base"

    def available(self) -> list[str]:
        """這個 client 真的能提供哪些面向。"""
        return []

    def raw(self, table: str, aspect: str, target: dict) -> dict | None:
        """原始 payload；拿不到回 None（該面向對該表視為 unavailable）。

        `target` 是 datahub.resolve_target() 的結果：urn、grant_key、
        quality_key——去平台哪裡拿，由 input 宣告或依表名推導。"""
        raise NotImplementedError


class NullClient(Client):
    """沒接 API 時的預設值：什麼都不抓，也不報錯。"""

    name = "none"

    def raw(self, table, aspect, target):
        return None


class FixtureClient(Client):
    """讀本地 JSON。格式就是 snapshot 的 `datasets` 段（已解析好的形狀），
    讓 API 沒好之前也能把整條流程跑通、也給測試一個確定性輸入。"""

    name = "fixture"

    def __init__(self, path: str):
        self.path = path
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        self.datasets = {str(k).lower(): v
                         for k, v in (data.get("datasets") or data).items()}
        self._available = data.get("available") or list(datahub.ASPECT_KEYS)

    def available(self):
        return [a for a in datahub.ASPECT_KEYS if a in self._available]

    def raw(self, table, aspect, target):
        entry = self.datasets.get(table.lower())
        if entry is None:
            return None
        field = _SNAPSHOT_FIELD[aspect]
        return {"__parsed__": entry[field]} if field in entry else None


class HttpClient(Client):
    """真連 DataHub GMS 與自建 API。

    **API ready 時要做的事只有兩件**：確認 `_ENDPOINTS` 的路徑、
    確認 `_PARSERS` 吃得下真實 payload。認證從環境變數來（設定檔不放 token）。"""

    name = f"datahub-{datahub.DATAHUB_VERSION}"

    def __init__(self, settings: dict, timeout: float = 10.0):
        self.settings = settings
        self.timeout = timeout
        self.bases = {api: datahub.expand_env(settings.get(key) or "")
                      for api, key in _BASE_KEY.items()}
        self.token = os.environ.get("DATAHUB_TOKEN", "")
        self.errors: list[str] = []

    def available(self):
        return [a for a in datahub.ASPECT_KEYS
                if self.bases.get(_ENDPOINTS[a]["api"])]

    def _request(self, url: str) -> dict | None:
        """唯一的網路出口。連不上／非 2xx 一律回 None（治理不因平台掛掉停擺）。"""
        import urllib.error
        import urllib.request
        request = urllib.request.Request(url, headers={
            "Accept": "application/json",
            **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
        })
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code != 404:      # 404＝平台上沒這個 aspect，是正常狀態
                self.errors.append(f"{url} → HTTP {error.code}")
            return None
        except Exception as error:
            self.errors.append(f"{url} → {error}")
            return None

    def raw(self, table, aspect, target):
        spec = _ENDPOINTS[aspect]
        base = self.bases.get(spec["api"], "").rstrip("/")
        if not base:
            return None
        from urllib.parse import quote
        key = target.get({"access_grant": "grant_key",
                          "quality_check": "quality_key"}.get(aspect, "urn"),
                         target.get("urn", ""))
        return self._request(base + spec["path"].format(
            urn=quote(str(target.get("urn", "")), safe=""),
            key=quote(str(key), safe="")))


def make_client(settings: dict) -> Client:
    """依設定挑 client：fixture > http > null。"""
    fixture = os.environ.get("DATAHUB_FIXTURE") or settings.get("fixture") or ""
    if fixture and os.path.isfile(fixture):
        return FixtureClient(fixture)
    if any(datahub.expand_env(settings.get(key) or "")
           for key in _BASE_KEY.values()):
        return HttpClient(settings)
    return NullClient()


# ------------------------------------------------------------------ 抓取

def fetch(tables: list[str], settings: dict,
          client: Client | None = None, targets: dict | None = None) -> dict:
    """抓一個 subject 的所有表 → snapshot dict（寫檔前的完整內容）。

    `targets`＝`input/<名>/datahub.yaml` 宣告的「去平台哪裡拿」；沒宣告的表
    依表名推導。snapshot 會把用過的位置記下來，報告才交代得出「我去哪裡找的」。"""
    from datetime import datetime, timezone
    client = client or make_client(settings)
    available = set(client.available())
    unavailable = [a for a in datahub.ASPECT_KEYS if a not in available]
    resolved = datahub.resolve_targets(list(tables), settings, targets)
    datasets: dict[str, dict] = {}
    for table in sorted(tables):
        target = resolved[table]
        entry: dict = {"urn": target["urn"], "exists": False,
                       "target_origin": target["origin"],
                       "link": target["link"]}
        for aspect in datahub.ASPECT_KEYS:
            if aspect not in available:
                continue
            payload = client.raw(table, aspect, target)
            if payload is None:
                continue
            value = (payload["__parsed__"] if "__parsed__" in payload
                     else _PARSERS[aspect](payload))
            entry[_SNAPSHOT_FIELD[aspect]] = value
            entry["exists"] = True
        datasets[table] = entry
    return {
        "schema_version": 1,
        "source": client.name,
        "fetched_at": datetime.now(timezone.utc).isoformat()
                              .replace("+00:00", "Z"),
        "server": datahub.expand_env(settings.get("server") or ""),
        "reason": ("尚未設定 server／fixture" if client.name == "none" else ""),
        "datasets": datasets,
        "unavailable": unavailable,
        "errors": list(getattr(client, "errors", [])),
    }
