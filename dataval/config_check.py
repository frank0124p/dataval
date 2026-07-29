"""Config 檔案格式檢查（pre-run lint）＋變更快取。

每次 run.py 啟動前，逐檔驗證 config/ 內四類知識輸入的格式是否符合 template
（各資料夾的 README 即 template）：

  <域>/erd/*.md|.mmd          ER 參考模型（```mermaid + erDiagram 可解析）
  <域>/erd/tables/*.md         參考表用途（檔名＝表名、標題一致、內容非空）
  <域>/flows/*.md|.flow.yaml   E2E 流程（flowchart 可解析／YAML stages 合法）
  <域>/naming/glossary.md|yaml 詞彙字典（段落與對照表列可解析）
  <域>/ssot/registry.yaml      SSOT registry（YAML mapping）

快取機制：驗證結果與檔案 SHA256 存 build/config_check.json——內容沒變的檔案
下次直接沿用結果、不重新解析；有變或新增的檔案才重驗。快取檔確定性
（排序、無時間戳），刪除的檔案會自動從快取移除。

knowhow 規則不在此檢查範圍：compile 已 fail-closed（壞規則直接中斷）。
此檢查**不擋** run.py（與「壞檔降級不靜默」哲學一致）；獨立 CLI 的
exit code 供 agent 修檔迴圈使用（0＝全過、1＝有格式問題）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import yaml

from .er_diagram import extract_mermaid, parse_mermaid
from . import flows as flows_mod

_TABLE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
CACHE_FORMAT = "dataval.config_check.v1"


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------- 逐類檢查

def _check_erd(path: str, text: str) -> list[str]:
    problems: list[str] = []
    if path.endswith(".md"):
        if "```mermaid" not in text:
            return ["缺 ```mermaid 區塊（ER 圖要放在 fence 內；見 erd/README.md）"]
        text = extract_mermaid(text)
    parsed = parse_mermaid(text)
    problems.extend(parsed["errors"])
    return problems


def _check_table_purpose(path: str, text: str) -> list[str]:
    problems: list[str] = []
    stem = os.path.splitext(os.path.basename(path))[0]
    if not _TABLE_NAME.match(stem):
        problems.append(f"檔名必須是表名（snake_case 全小寫）：{stem}")
    lines = text.strip().splitlines()
    body = lines
    if lines and lines[0].lstrip().startswith("#"):
        heading = lines[0].lstrip("# ").strip()
        if heading and heading != stem:
            problems.append(f"標題「{heading}」與檔名（表名）「{stem}」不一致")
        body = lines[1:]
    if not "\n".join(body).strip():
        problems.append("內容是空的（至少寫一段這張表的用途）")
    return problems


def _check_flow_md(path: str, text: str) -> list[str]:
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        flows_mod.parse_flow_md(text, name)
        return []
    except Exception as error:
        return [f"{type(error).__name__}: {error}"]


def _check_flow_yaml(path: str, text: str) -> list[str]:
    try:
        spec = yaml.safe_load(text) or {}
        if not isinstance(spec, dict):
            raise ValueError("根節點必須是 mapping")
        stages = spec.get("stages")
        if not isinstance(stages, list) or not stages:
            raise ValueError("缺 stages 清單")
        for i, stage in enumerate(stages, start=1):
            if not isinstance(stage, dict) or not stage.get("name"):
                raise ValueError(f"第 {i} 站缺 name")
            kind = stage.get("kind", "table")
            if kind not in flows_mod.VALID_KINDS:
                raise ValueError(f"第 {i} 站 kind '{kind}' 不合法"
                                 f"（限 {'/'.join(flows_mod.VALID_KINDS)}）")
        return []
    except Exception as error:
        return [f"{type(error).__name__}: {error}"]


def _check_glossary_md(path: str, text: str) -> list[str]:
    from .engine import _glossary_from_md
    try:
        _glossary_from_md(text)
        return []
    except Exception as error:
        return [f"{type(error).__name__}: {error}"]


def _check_glossary_yaml(path: str, text: str) -> list[str]:
    try:
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("根節點必須是 mapping")
        for key in ("banned_terms", "aliases"):
            value = data.get(key) or {}
            if not isinstance(value, dict):
                raise ValueError(f"{key} 必須是「詞: 標準詞」對照表")
        terms = data.get("standard_terms") or []
        if not isinstance(terms, list):
            raise ValueError("standard_terms 必須是清單")
        return []
    except Exception as error:
        return [f"{type(error).__name__}: {error}"]


def _check_yaml_mapping(path: str, text: str) -> list[str]:
    try:
        data = yaml.safe_load(text)
        if data is not None and not isinstance(data, dict):
            raise ValueError("根節點必須是 mapping")
        return []
    except Exception as error:
        return [f"{type(error).__name__}: {error}"]


# ---------------------------------------------------------------- 掃描與快取

def _scan(config_dir: str) -> list[tuple[str, str]]:
    """回傳 [(相對路徑, 檢查類型)]，排序固定。"""
    out: list[tuple[str, str]] = []
    for dom in sorted(os.listdir(config_dir)):
        dom_path = os.path.join(config_dir, dom)
        if not os.path.isdir(dom_path) or dom.startswith("_"):
            continue

        erd_dir = os.path.join(dom_path, "erd")
        if os.path.isdir(erd_dir):
            for fn in sorted(os.listdir(erd_dir)):
                if fn.lower().startswith("readme"):
                    continue
                if fn.endswith((".md", ".mmd", ".mermaid")):
                    out.append((f"{dom}/erd/{fn}", "erd"))
            tables_dir = os.path.join(erd_dir, "tables")
            if os.path.isdir(tables_dir):
                for fn in sorted(os.listdir(tables_dir)):
                    if fn.endswith(".md") and not fn.lower().startswith("readme"):
                        out.append((f"{dom}/erd/tables/{fn}", "table_purpose"))

        flows_dir = os.path.join(dom_path, "flows")
        if os.path.isdir(flows_dir):
            for fn in sorted(os.listdir(flows_dir)):
                if fn.lower().startswith("readme"):
                    continue
                if fn.endswith(".md"):
                    out.append((f"{dom}/flows/{fn}", "flow_md"))
                elif fn.endswith((".flow.yaml", ".flow.yml")):
                    out.append((f"{dom}/flows/{fn}", "flow_yaml"))

        naming_dir = os.path.join(dom_path, "naming")
        if os.path.isdir(naming_dir):
            if os.path.isfile(os.path.join(naming_dir, "glossary.md")):
                out.append((f"{dom}/naming/glossary.md", "glossary_md"))
            if os.path.isfile(os.path.join(naming_dir, "glossary.yaml")):
                out.append((f"{dom}/naming/glossary.yaml", "glossary_yaml"))

        ssot = os.path.join(dom_path, "ssot", "registry.yaml")
        if os.path.isfile(ssot):
            out.append((f"{dom}/ssot/registry.yaml", "yaml_mapping"))
    return out


_CHECKERS = {
    "erd": _check_erd,
    "table_purpose": _check_table_purpose,
    "flow_md": _check_flow_md,
    "flow_yaml": _check_flow_yaml,
    "glossary_md": _check_glossary_md,
    "glossary_yaml": _check_glossary_yaml,
    "yaml_mapping": _check_yaml_mapping,
}


def run_check(config_dir: str, cache_path: str) -> dict:
    """逐檔檢查（有快取）。回傳摘要 dict；快取檔只在內容變動時改寫。"""
    cache: dict = {}
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                loaded = json.load(f)
            if loaded.get("format") == CACHE_FORMAT:
                cache = loaded.get("files", {})
        except Exception:
            cache = {}

    files: dict[str, dict] = {}
    checked = cached = 0
    problems: dict[str, list[str]] = {}
    for rel, kind in _scan(config_dir):
        path = os.path.join(config_dir, *rel.split("/"))
        digest = _sha256(path)
        prior = cache.get(rel)
        if prior and prior.get("sha256") == digest and prior.get("kind") == kind:
            entry = prior
            cached += 1
        else:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            found = _CHECKERS[kind](path, text)
            entry = {"sha256": digest, "kind": kind, "problems": found}
            checked += 1
        files[rel] = entry
        if entry["problems"]:
            problems[rel] = entry["problems"]

    payload = {"format": CACHE_FORMAT, "files": files}
    previous = None
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                previous = json.load(f)
        except Exception:
            previous = None
    if previous != payload:
        os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)

    return {"total": len(files), "checked": checked, "cached": cached,
            "problems": problems}


def console_lines(summary: dict) -> list[str]:
    total, cached = summary["total"], summary["cached"]
    problems = summary["problems"]
    if not problems:
        return [f"Config 格式檢查：✅ {total} 檔全部通過"
                f"（快取沿用 {cached}、本次實檢 {summary['checked']}）"]
    lines = [f"Config 格式檢查：❌ {len(problems)}/{total} 檔有格式問題"
             f"（快取沿用 {cached}）："]
    for rel in sorted(problems):
        for problem in problems[rel]:
            lines.append(f"  ❌ config/{rel}：{problem}")
    lines.append("  👉 請依各資料夾 README 的 template 修正上述檔案後重跑"
                 "（沒改的檔案有快取，不會重驗）。")
    return lines
