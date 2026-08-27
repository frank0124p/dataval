#!/usr/bin/env python3
"""零參數自動執行：掃 input/ 下所有 DDL，逐一驗證並把報告寫到 govern_doc/。

用法（在專案根目錄）：
    python run.py                # 跑 input/ 下所有 subject
    python run.py order          # 只跑指定 subject（可多個；
                                 #   也接受 input/order 或 order.sql 寫法）

行為：
  - 自動找 input/ 裡的 *.sql / *.ddl
  - 自動載入每個 subject 的 samples、relations.yaml 與 context.md
  - 自動載入 config/<域>/knowhow 與 Common/knowhow_py 裡的規則
  - 每個 DDL 都產生 govern_doc/<名稱>/<名稱>.report.{md,json,html}
    （🎨 design mode 的設計文件則走 design_doc/<名稱>/）
  - LLM 看環境變數 DATAVAL_LLM_BASE_URL；沒設就只跑閘門區（仍能出合規判定）
"""
from __future__ import annotations
import json
import os
import sys
from dataclasses import dataclass
import yaml

from dataval.engine import load_config, validate
from dataval.report import (to_json, to_markdown, to_html, summarize,
                            blocking_summary, check_origins,
                            table_finding_counts)
from dataval.llm import from_env
from dataval.advisory_export import build_advisory_prompt
from dataval.subject_summary import build_summary
from dataval.compiler import RuleLoadError, ensure_compiled
from dataval import rules_history
from dataval.er_diagram import parse_mermaid
from dataval.parser import parse_ddl
from dataval.model import Finding, ZONE_ADVISORY, ZONE_GATING
from dataval import precheck as preflight
from dataval.provenance import validation_manifest
from dataval import docpaths

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.environ.get("DATAVAL_INPUT_DIR", os.path.join(HERE, "input"))
# 文件根：產出走 <root>/design_doc/<subject>/ 與 <root>/govern_doc/<subject>/
# （一 subject 一資料夾；覆寫見 dataval/docpaths.py）
DOC_ROOT = docpaths.doc_root(HERE)
CONFIG = os.path.join(HERE, "config", "_engine", "default.yaml")
CONFIG_DIR = os.path.join(HERE, "config")
DOMAIN_ROOT = os.path.join(HERE, "config")
RULES_ROOT = os.path.join(HERE, "config", "Common", "knowhow_py")
CASE_CONFIG_ROOT = os.environ.get(
    "DATAVAL_CASE_CONFIG_DIR", "")
ER_DIAGRAM_ROOT = os.environ.get(
    "DATAVAL_ER_DIAGRAM_DIR", "")
PRODUCTION_ROOT = os.path.join(HERE, "production")
# 迭代歷史根目錄：標準 input/ 走 repo 的 iterations/；
# 以 DATAVAL_INPUT_DIR 跑範例／臨時輸入時，歷史跟著文件根走，
# 不汙染 repo 的正式迭代紀錄。可用 DATAVAL_ITERATIONS_DIR 覆寫。
ITERATIONS_ROOT = os.environ.get("DATAVAL_ITERATIONS_DIR") or (
    os.path.join(DOC_ROOT, "iterations")
    if os.environ.get("DATAVAL_INPUT_DIR")
    else os.path.join(HERE, "iterations"))


@dataclass
class InputCase:
    ddl: str
    sample: dict | None
    context: str
    domains: list[str]
    business_keys: dict[str, list[str]]
    lineage: dict | None
    relations: list | None
    er_diagram: dict | None
    config_source: str
    diagnostics: list[Finding]
    # 迭代問答（選填第四件；legacy 模式不支援，維持 None）
    answers: dict | None = None
    answers_problems: list[str] | None = None
    answers_file: str = ""
    # 衍生 SQL（選填第五件）
    derivation: dict | None = None
    derivation_problems: list[str] | None = None
    derivation_file: str = ""
    # 多檔 DDL：表名（小寫）→ 來源檔名
    table_files: dict | None = None


def find_ddls() -> list[str]:
    """掃 input/。標準佈局：一 subject 一資料夾 input/<名>/<名>.sql；
    舊式平鋪 input/<名>.sql 相容。"""
    if not os.path.isdir(INPUT_DIR):
        return []
    out = []
    for entry in sorted(os.listdir(INPUT_DIR)):
        path = os.path.join(INPUT_DIR, entry)
        if os.path.isdir(path):
            if entry.endswith(".samples"):
                continue  # 舊式平鋪的樣本資料夾
            for ext in (".sql", ".ddl"):
                ddl = os.path.join(path, entry + ext)
                if os.path.isfile(ddl):
                    out.append(ddl)
                    break
        elif entry.lower().endswith((".sql", ".ddl")):
            out.append(path)
    return out


def _input_diagnostic(check_id: str, target: str, message: str,
                      *, blocking: bool = False) -> Finding:
    return Finding(check_id, "structural", "fail" if blocking else "warning",
                   target, message, severity="error" if blocking else "warning",
                   source="rule", zone=ZONE_GATING,
                   expected="config/cases 設定可正確讀取與解析",
                   actual=message, fix=f"修正檔案 {target}")


def _case_search_roots(case_root: str = "") -> list[str]:
    """個案設定的搜尋順序：環境變數指定 → 各 domain 的 cases/ →
    引擎層 _engine/cases/（內部 fixtures）。"""
    if case_root:
        return [case_root]
    roots = []
    cfg_root = os.path.join(HERE, "config")
    for entry in sorted(os.listdir(cfg_root)):
        dpath = os.path.join(cfg_root, entry, "cases")
        if not entry.startswith("_") and os.path.isdir(dpath):
            roots.append(dpath)
    engine_cases = os.path.join(cfg_root, "_engine", "cases")
    if os.path.isdir(engine_cases):
        roots.append(engine_cases)
    return roots


def case_config_for(ddl_path: str, diagnostics: list[Finding] | None = None,
                    case_root: str = CASE_CONFIG_ROOT) -> tuple[dict, str]:
    """搜尋 config/<域>/cases/<DDL 名>.yaml（個案補充設定）。"""
    name = os.path.splitext(os.path.basename(ddl_path))[0]
    candidates = [os.path.join(root, name + ext)
                  for root in _case_search_roots(case_root)
                  for ext in (".yaml", ".yml")]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        source = os.path.relpath(path, HERE).replace(os.sep, "/")
        try:
            with open(path, encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
            if not isinstance(spec, dict):
                raise ValueError("根節點必須是 mapping")
            return spec, source
        except Exception as e:
            if diagnostics is not None:
                diagnostics.append(_input_diagnostic(
                    "SYSTEM.CASE_CONFIG", source,
                    f"case config 解析失敗：{type(e).__name__}: {e}",
                    blocking=True))
            return {}, source
    return {}, ""


def sample_for(spec: dict, source: str,
               diagnostics: list[Finding] | None = None) -> dict | None:
    sample = spec.get("sample_data")
    if sample is None:
        return None
    if isinstance(sample, dict):
        return sample
    if diagnostics is not None:
        diagnostics.append(_input_diagnostic(
            "SYSTEM.SAMPLE_SPEC", source,
            "sample_data 必須是 table -> rows 對照"))
    return None


def context_for(spec: dict, source: str,
                diagnostics: list[Finding] | None = None) -> str:
    context = spec.get("context", "")
    if isinstance(context, str):
        return context.strip()
    if diagnostics is not None:
        diagnostics.append(_input_diagnostic(
            "SYSTEM.CONTEXT_SPEC", source, "context 必須是文字"))
    return ""


def domains_for(spec: dict, source: str,
                diagnostics: list[Finding] | None = None) -> list[str]:
    domains = spec.get("domains")
    if domains is None:
        return []
    if isinstance(domains, list) and all(isinstance(domain, str) for domain in domains):
        return domains
    if diagnostics is not None:
        diagnostics.append(_input_diagnostic(
            "SYSTEM.DOMAIN_SPEC", source, "domains 必須是字串 list"))
    return []


def keys_for(spec: dict, source: str,
             diagnostics: list[Finding] | None = None) -> dict[str, list[str]]:
    keys = spec.get("business_keys")
    if keys is None:
        return {}
    try:
        if not isinstance(keys, dict):
            raise ValueError("business_keys 必須是 table -> columns 對照")
        normalized: dict[str, list[str]] = {}
        for table, columns in keys.items():
            if not isinstance(columns, list) or not columns:
                raise ValueError(f"{table} 的 business key 必須是非空 list")
            normalized[str(table)] = [str(column) for column in columns]
        return normalized
    except Exception as e:
        if diagnostics is not None:
            diagnostics.append(_input_diagnostic(
                "SYSTEM.BUSINESS_KEY_SPEC", source,
                f"business_keys 設定錯誤：{type(e).__name__}: {e}",
                blocking=True))
        return {}


def lineage_for(spec: dict, source: str,
                diagnostics: list[Finding] | None = None) -> dict | None:
    """Load optional explicit design-lineage metadata from the case config."""
    if "lineage" not in spec:
        return None
    lineage = spec.get("lineage")
    if isinstance(lineage, dict):
        return {"lineage": lineage}
    if diagnostics is not None:
        diagnostics.append(_input_diagnostic(
            "SYSTEM.LINEAGE_SPEC", source,
            "lineage 必須是 target table -> relation 的 mapping",
            blocking=True))
    # Empty dict means a declaration exists but is invalid. This avoids
    # turning broken config into a non-blocking suggestion.
    return {}


def er_diagram_for(ddl_path: str, diagnostics: list[Finding] | None = None,
                   er_root: str = ER_DIAGRAM_ROOT) -> dict | None:
    """搜尋個案 ER 圖：config/<域>/cases/<名>.mmd 或 _engine/er_diagrams/。"""
    name = os.path.splitext(os.path.basename(ddl_path))[0]
    for extension in (".mmd", ".mermaid", ".md"):
        roots = ([er_root] if er_root else
                 _case_search_roots() +
                 [os.path.join(HERE, "config", "_engine", "er_diagrams")])
        path = next((p for p in (os.path.join(r, name + extension)
                                 for r in roots)
                     if os.path.isfile(p)),
                    os.path.join(roots[-1], name + extension))
        if not os.path.isfile(path):
            continue
        source = os.path.relpath(path, HERE).replace(os.sep, "/")
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if extension == ".md":
                from dataval.er_diagram import extract_mermaid
                text = extract_mermaid(text)
            diagram = parse_mermaid(text, source=source)
        except Exception as e:
            if diagnostics is not None:
                diagnostics.append(Finding(
                    "SYSTEM.ER_DIAGRAM_PARSE", "lineage", "info", source,
                    f"ER diagram 讀取失敗：{type(e).__name__}: {e}",
                    severity="info", source="rule", zone=ZONE_ADVISORY,
                    fix="修正 Mermaid ER diagram；此問題不影響閘門判定。"))
            return None
        if diagram["errors"] and diagnostics is not None:
            diagnostics.append(Finding(
                "SYSTEM.ER_DIAGRAM_PARSE", "lineage", "info", source,
                "ER diagram 有無法解析的內容：" + "；".join(diagram["errors"]),
                severity="info", source="rule", zone=ZONE_ADVISORY,
                fix="依 config/<域>/erd/README.md 修正 Mermaid 語法。"))
        return diagram
    return None


def load_input(ddl_path: str) -> InputCase:
    """Read one DDL and its same-named config/cases YAML once."""
    diagnostics: list[Finding] = []
    try:
        with open(ddl_path, encoding="utf-8") as f:
            ddl = f.read()
    except Exception as e:
        ddl = ""
        diagnostics.append(_input_diagnostic(
            "SYSTEM.DDL_READ", ddl_path,
            f"DDL 讀取失敗：{type(e).__name__}: {e}", blocking=True))
    spec, config_source = case_config_for(ddl_path, diagnostics)
    return InputCase(
        ddl=ddl,
        sample=sample_for(spec, config_source, diagnostics),
        context=context_for(spec, config_source, diagnostics),
        domains=domains_for(spec, config_source, diagnostics),
        business_keys=keys_for(spec, config_source, diagnostics),
        lineage=lineage_for(spec, config_source, diagnostics),
        relations=None,
        er_diagram=er_diagram_for(ddl_path, diagnostics),
        config_source=config_source,
        diagnostics=diagnostics,
    )


def load_input_v2(ddl_path: str,
                  pre: "preflight.PrecheckResult") -> InputCase:
    """前置檢核通過後，把四件輸入合併成 InputCase。

    config/<域>/cases/<名>.yaml 仍可提供補充設定（如 business_keys、額外 lineage），
    但四件輸入是權威來源：samples 只取 CSV、context 只取 context.md、
    relations.yaml 轉出的 lineage 以表為單位優先於 cases 的 lineage。
    """
    diagnostics: list[Finding] = list(pre.diagnostics)
    spec, config_source = case_config_for(ddl_path, diagnostics)

    business_keys = keys_for(spec, config_source, diagnostics)
    business_keys.update(pre.business_keys)  # front-matter 優先

    legacy_lineage = lineage_for(spec, config_source, diagnostics)
    lineage: dict | None = pre.lineage_spec
    if legacy_lineage and isinstance(legacy_lineage.get("lineage"), dict):
        merged = dict(legacy_lineage["lineage"])
        merged.update((lineage or {}).get("lineage", {}))  # relations 優先
        lineage = {"lineage": merged}

    domains = pre.domains or domains_for(spec, config_source, diagnostics)

    return InputCase(
        ddl=pre.ddl,
        sample=pre.samples or None,
        context=pre.context_text,
        domains=domains,
        business_keys=business_keys,
        lineage=lineage,
        relations=pre.relations,
        er_diagram=merge_domain_erds(
            er_diagram_for(ddl_path, diagnostics), domains,
            {t.name for t in parse_ddl(pre.ddl).tables},
            diagnostics),
        config_source=config_source,
        diagnostics=diagnostics,
        answers=pre.answers_data,
        answers_problems=pre.answers_problems,
        answers_file=pre.answers_file,
        derivation=pre.derivation_data,
        derivation_problems=pre.derivation_problems,
        derivation_file=pre.derivation_file,
        table_files=pre.table_files,
    )


def merge_domain_erds(er_diagram: dict | None, domains: list[str] | None,
                      ddl_table_names: set[str],
                      diagnostics: list[Finding],
                      droot: str | None = None) -> dict | None:
    """疊加 domain 參考 ER 模型（config/<域>/erd/*.md）。

    關係：只取「兩端表都出現在本次 DDL」的，供 LINEAGE.ER_SUGGESTION 比對。
    entity 欄位定義：對得上本次 DDL 的表就併入，供 ERD.ENTITY_REFERENCE
    做確定性欄位對照。個案 ER 圖（config/<域>/cases/<名>.mmd）優先。
    """
    droot = droot or os.path.join(HERE, "config")
    folders = {f.lower(): f for f in os.listdir(droot)
               if os.path.isdir(os.path.join(droot, f))
               and not f.startswith("_")}
    lower_names = {n.lower() for n in ddl_table_names}
    merged = {"source": (er_diagram or {}).get("source", ""),
              "entities": dict((er_diagram or {}).get("entities") or {}),
              "relationships": list((er_diagram or {}).get("relationships") or []),
              "errors": []}
    seen_rel = {(r.get("left"), r.get("right"), r.get("label"))
                for r in merged["relationships"]}
    added = False
    seen_dom: set[str] = set()
    for want in ["Common"] + [d for d in (domains or []) if d]:
        folder = folders.get(want.strip().lower())
        if not folder or folder in seen_dom:
            continue
        seen_dom.add(folder)
        erd_dir = os.path.join(droot, folder, "erd")
        if not os.path.isdir(erd_dir):
            continue
        for fn in sorted(os.listdir(erd_dir)):
            # 標準格式 .md（```mermaid fence）；舊式 .mmd/.mermaid 相容。
            # README 與 tables/（參考表用途）不是 ER 圖。
            if not fn.endswith((".mmd", ".mermaid", ".md")):
                continue
            if fn.lower().startswith("readme"):
                continue
            label = f"{folder}/erd/{fn}"
            try:
                with open(os.path.join(erd_dir, fn), encoding="utf-8") as f:
                    text = f.read()
                if fn.endswith(".md"):
                    from dataval.er_diagram import extract_mermaid
                    text = extract_mermaid(text)
                parsed = parse_mermaid(text, source=label)
            except Exception as e:
                diagnostics.append(_input_diagnostic(
                    "SYSTEM.ER_DIAGRAM_PARSE", label,
                    f"domain ER 模型讀取失敗：{type(e).__name__}: {e}"))
                continue
            if parsed.get("errors"):
                diagnostics.append(_input_diagnostic(
                    "SYSTEM.ER_DIAGRAM_PARSE", label,
                    "domain ER 模型有無法解析的行：" + "；".join(parsed["errors"][:3])))
            for rel in parsed.get("relationships") or []:
                left, right = str(rel.get("left")), str(rel.get("right"))
                if left.lower() not in lower_names or right.lower() not in lower_names:
                    continue
                key = (rel.get("left"), rel.get("right"), rel.get("label"))
                if key in seen_rel:
                    continue
                seen_rel.add(key)
                merged["relationships"].append(rel)
                for name in (left, right):
                    merged["entities"].setdefault(
                        name, {"name": name, "columns": []})
                added = True
            # 參考模型的 entity 欄位定義：對得上本次 DDL 的表就併入，
            # 供 ERD.ENTITY_REFERENCE 做確定性欄位對照（先載入者優先）。
            for name, ent in (parsed.get("entities") or {}).items():
                if name.lower() not in lower_names or not ent.get("columns"):
                    continue
                target = merged["entities"].setdefault(
                    name, {"name": name, "columns": []})
                if not target.get("columns"):
                    target["columns"] = list(ent["columns"])
                    target["source"] = label
                added = True
    if er_diagram is None and not added:
        return None
    if not merged["source"]:
        merged["source"] = "(domain erd 參考模型)"
    return merged


def _subject_key(spec: str) -> str:
    """指定寫法正規化：order／input/order／order.sql → order。"""
    return os.path.splitext(os.path.basename(os.path.normpath(spec)))[0]


def select_subjects(ddls: list[str], wanted: list[str]) -> tuple[list[str], list[str]]:
    """依指定的 subject 過濾 DDL 清單——只跑點名的資料夾，其餘不動。
    接受名稱（order）、資料夾路徑（input/order）或檔名（order.sql）。
    回傳 (選中的 ddls, 對不上的指定)。空指定＝全跑。"""
    if not wanted:
        return ddls, []
    by_name = {os.path.splitext(os.path.basename(p))[0]: p for p in ddls}
    selected, unknown = [], []
    for w in wanted:
        name = _subject_key(w)
        if name in by_name:
            if by_name[name] not in selected:
                selected.append(by_name[name])
        else:
            unknown.append(w)
    return selected, unknown


def write_report_outputs(name: str, round_no: int, outputs: dict[str, str],
                         report_dir: str = "",
                         proposal: dict | None = None) -> str:
    """報告三式落地：<名>.report.* 是最新版的固定入口（工具與晉升流程依賴）；
    另存 <名>.round_<N>.report.*——檔名標明輪次，每輪各留一份。
    有建議 DDL 時，建議 Join SQL 與未來寬表 DDL 一併拆檔進報告產出：
    <名>.round_<N>.join.sql／<名>.round_<N>.future.ddl。
    回傳輪次版 HTML 路徑。"""
    report_dir = report_dir or docpaths.govern_dir(DOC_ROOT, name)
    for suffix, content in outputs.items():
        for fname in (name + suffix, f"{name}.round_{round_no}{suffix}"):
            with open(os.path.join(report_dir, fname), "w",
                      encoding="utf-8") as f:
                f.write(content)
    if proposal:
        from dataval import iterations as iter_history
        texts = iter_history.proposal_file_texts(
            name, round_no, proposal,
            proposal_md_ref=f"iterations/{name}/round_{round_no}.proposal.md")
        for kind, text in texts.items():
            with open(os.path.join(
                    report_dir, f"{name}.round_{round_no}.{kind}"), "w",
                    encoding="utf-8") as f:
                f.write(text)
    return os.path.join(report_dir, f"{name}.round_{round_no}.report.html")


def pending_advisory_specs(findings: list[Finding], compiled_path: str) -> list[dict]:
    pending_ids = {
        f.check_id.replace("SKILL.", "", 1)
        for f in findings
        if f.zone == "advisory" and f.status == "skipped" and
        f.check_id.startswith("SKILL.")
    }
    with open(compiled_path, encoding="utf-8") as f:
        compiled = json.load(f)
    specs = []
    for rule in compiled.get("rules", []):
        if rule.get("id") not in pending_ids or rule.get("kind") != "check-llm":
            continue
        specs.append({
            "id": rule["id"],
            "title": rule.get("title") or rule["id"],
            "domain": rule.get("domain", "Common"),
            "desc": rule.get("check_llm") or "(未提供 check-llm 內容)",
        })
    return specs


def main():
    strict = ("--strict" in sys.argv or
              os.environ.get("DATAVAL_STRICT", "").strip().lower() in
              {"1", "true", "yes", "on"})
    os.makedirs(docpaths.design_root(DOC_ROOT), exist_ok=True)
    os.makedirs(docpaths.govern_root(DOC_ROOT), exist_ok=True)
    design_root_label = docpaths.label(docpaths.design_root(DOC_ROOT), HERE)
    govern_root_label = docpaths.label(docpaths.govern_root(DOC_ROOT), HERE)
    from dataval import design as design_mod
    from dataval import design_report, etl_manifest
    ddls = find_ddls()                                      # 🛡 govern mode
    design_subjects = design_mod.find_design_subjects(INPUT_DIR)  # 🎨 design mode
    if not ddls and not design_subjects:
        print(f"找不到任何 subject。請把 .sql（govern）或 context.md（design）"
              f"放進：{INPUT_DIR}")
        sys.exit(0)
    # 指定 subject 時只跑點名的資料夾（python run.py order …），其餘不動。
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")]
    ddls, unknown = select_subjects(ddls, wanted)
    if wanted:
        keys = {_subject_key(w) for w in wanted}
        design_subjects = [s for s in design_subjects if s[0] in keys]
        unknown = [w for w in unknown
                   if _subject_key(w) not in {s[0] for s in design_subjects}]
    if unknown:
        available = "、".join(
            sorted({os.path.splitext(os.path.basename(p))[0]
                    for p in find_ddls()}
                   | {s[0] for s in design_mod.find_design_subjects(INPUT_DIR)}))
        print(f"找不到指定的 subject：{'、'.join(unknown)}。"
              f"可用：{available}", file=sys.stderr)
        sys.exit(2)
    if wanted:
        print("只跑指定 subject："
              + "、".join([os.path.splitext(os.path.basename(p))[0]
                           for p in ddls] + [s[0] for s in design_subjects]))

    cfg = load_config(CONFIG)

    # 正式區資產索引：把 production/ 的已核准主體寫成 config/Common/
    # production/registry.md——放 Common ⇒ 所有 domain 都載入，且在設計素材
    # 索引裡標必讀。內容確定性，沒變不改寫。
    from dataval import prodassets
    prod_assets = prodassets.scan(PRODUCTION_ROOT)
    _, registry_changed = prodassets.write_registry(CONFIG_DIR, prod_assets)
    if registry_changed:
        print(f"正式區資產索引 → config/{prodassets.REGISTRY_REL}"
              f"（{len(prod_assets)} 個已核准主體）")

    # Config 格式正規化（pre-run auto-format）：依資料夾路徑把 config 檔案
    # 補成引擎吃得下的格式（包 ```mermaid fence、補標題、補段落標題、
    # 改副檔名），只補格式與結構、不動語意內容。已正確的檔案不改寫。
    # 【預設啟用】關閉方式：DATAVAL_CONFIG_FORMAT=0。
    if os.environ.get("DATAVAL_CONFIG_FORMAT", "1").strip().lower() not in \
            {"0", "false", "no", "off"}:
        from dataval import config_format as cfg_format
        format_summary = cfg_format.run_format(CONFIG_DIR)
        if format_summary["changed"]:
            for line in cfg_format.console_lines(format_summary):
                print(line)

    # Config 格式檢查（pre-run lint，有快取：沒變的檔案不重驗）。
    # 【預設停用】啟用方式：環境變數 DATAVAL_CONFIG_CHECK=1，
    # 或把下行的預設值 "0" 改成 "1"。隨時可手動跑：python config_check.py
    if os.environ.get("DATAVAL_CONFIG_CHECK", "0").strip().lower() in \
            {"1", "true", "yes", "on"}:
        from dataval import config_check as cfg_check
        check_summary = cfg_check.run_check(
            CONFIG_DIR, os.path.join(HERE, "build", "config_check.json"))
        for line in cfg_check.console_lines(check_summary):
            print(line)

    # 規則 compile：每次重建結構化內容，有變更才寫入 JSON。
    compiled_target = os.path.join(HERE, "build", "compiled_rules.json")
    previous_rules_text = None
    if os.path.isfile(compiled_target):
        with open(compiled_target, encoding="utf-8") as f:
            previous_rules_text = f.read()
    try:
        compiled_path, recompiled = ensure_compiled(
            DOMAIN_ROOT, RULES_ROOT, compiled_target)
    except RuleLoadError as e:
        print(f"❌ 規則檔載入失敗：\n{e}", file=sys.stderr)
        print("修正上述檔案後重跑；格式見 SKILL_AUTHORING.md。", file=sys.stderr)
        sys.exit(1)
    print(("規則有更新 → 已重新 compile：" if recompiled else "規則未變 → 沿用既有 compile：")
          + os.path.relpath(compiled_path, HERE))
    # 規則版控：與 rules_history 最新快照比對——即使 bundle 先被
    # 測試／其他流程寫上磁碟（run.py 看到「未變」），漏帳仍會補記。
    with open(compiled_path, encoding="utf-8") as f:
        new_rules_text = f.read()
    snapshot = rules_history.ensure_recorded(
        new_rules_text, os.path.join(HERE, "rules_history"),
        previous_text=previous_rules_text if recompiled else None)
    if snapshot:
        print("規則版控 → 已記錄變更："
              + os.path.relpath(snapshot, HERE)
              + "（摘要見 rules_history/CHANGELOG.md）")
    llm = from_env()
    llm_on = type(llm).__name__ != "NullLLM"

    precheck_mode = os.environ.get("DATAVAL_PRECHECK", "strict").strip().lower()
    print(f"找到 {len(ddls) + len(design_subjects)} 個 subject"
          f"（🛡 govern {len(ddls)}、🎨 design {len(design_subjects)}）；"
          f"LLM：{'已接' if llm_on else '未接（只跑閘門區）'}"
          + ("" if precheck_mode != "legacy" else "；前置檢核：legacy（相容模式）"))

    # ── 🎨 design mode：只有 context.md、還沒有 DDL 的 subject ─────────
    # 治理（govern）走下方閘門迴圈；設計（design）在此產 prompt／渲染設計稿。
    # 素材索引審閱表（全 config；🤖=自動摘要，維護方式見表頭）
    with open(os.path.join(docpaths.design_root(DOC_ROOT),
                           "design_index_review.md"),
              "w", encoding="utf-8") as f:
        f.write(design_mod.index_review_md(CONFIG_DIR))
    design_pending: list[str] = []
    for name, folder in design_subjects:
        ddir = docpaths.design_dir(DOC_ROOT, name)
        dlabel = docpaths.label(ddir, HERE)
        with open(os.path.join(folder, "context.md"), encoding="utf-8") as f:
            ctx = f.read()
        # 設計問答：已答條目帶入 prompt（已澄清、勿重問）
        qa_path = design_mod.answers_file(folder)
        qa_data, qa_problems = design_mod.load_design_answers(qa_path)
        # 正式區資產：把可複用清單與（上一輪設計稿的）確定性候選餵進 prompt，
        # 讓 agent 用語意判讀「這件事是不是已經有人做過了」
        prior = {}
        prior_path = os.path.join(ddir, name + ".design_result.json")
        if os.path.isfile(prior_path):
            try:
                with open(prior_path, encoding="utf-8") as f:
                    prior = json.load(f)
            except Exception:
                prior = {}
        prior_hits = prodassets.referenced_by_design(prior, prod_assets)
        prompt = design_mod.build_design_prompt(
            name, ctx, CONFIG_DIR, compiled_path, answers=qa_data,
            production_material=prodassets.advisory_material(
                prod_assets,
                prodassets.candidates(prodassets.design_pairs(prior),
                                      prod_assets, prior_hits),
                prior_hits))
        with open(os.path.join(ddir, name + ".design_prompt.md"),
                  "w", encoding="utf-8") as f:
            f.write(prompt)
        result_path = os.path.join(ddir, name + ".design_result.json")
        if not os.path.isfile(result_path):
            design_pending.append(name)
            print(f"  🎨 {name}: design mode ｜ 尚無設計稿 → 待 agent 依 "
                  f"{dlabel}/{name}.design_prompt.md 產出 design_result")
            continue
        try:
            with open(result_path, encoding="utf-8") as f:
                design_result = json.load(f)
        except Exception as e:
            design_pending.append(name)
            print(f"  🎨 {name}: design mode ｜ design_result 讀取失敗（{e}），"
                  "視同待補")
            continue
        errors = design_mod.validate_design_result(design_result)
        if errors:
            design_pending.append(name)
            print(f"  🎨 {name}: design_result 不符 "
                  "config/_engine/design_result.schema.json：")
            for err in errors:
                print(f"     - {err}")
            continue
        # 閘門預檢：用現行規則試跑草稿 DDL（零 LLM；設計參考、非正式判定）
        ctx_meta, _ = design_mod.parse_context(ctx)
        ctx_domains = [str(d) for d in (ctx_meta.get("domains") or [])]
        try:
            from dataval.llm import NullLLM
            # 設計預檢**不套用** BUSINESS_KEY.METADATA：context.md 的
            # business_keys 講的是**來源表**的鍵，而設計出來的表（積木／寬表）
            # 是整合來源後的新表、名稱本來就不同，硬比一定對不上。
            # 設計稿自己的 key 宣告另有把關——validate_design_result 會驗
            # 每張表的 keys.business_key 欄位確實存在於該表的 columns。
            _, pf, pm = validate(
                design_mod.combined_ddl(design_result), cfg, context=ctx,
                business_keys={},
                llm=NullLLM(), domain_root=DOMAIN_ROOT, rules_root=RULES_ROOT,
                domains=ctx_domains,
                config_dir=CONFIG_DIR, production_root=PRODUCTION_ROOT)
            pf = [f for f in pf if f.check_id not in design_mod.PREVIEW_SKIP]
            ps, pbs = summarize(pf), blocking_summary(pf)
            # 依據追溯：預檢被卡／警告的每條規則附 config 來源檔
            origins = check_origins(pf, pm)
            blocked = [b["rule"] for b in pbs["blocked"]]
            warned = [b["rule"] for b in pbs["warned"]]
            preview = {"compliant": ps["compliant"], "fail": ps["fail"],
                       "warning": ps["warning"], "blocked": blocked,
                       "warned": warned,
                       "origins": {r: origins.get(r, "")
                                   for r in blocked + warned},
                       "skipped_rules": sorted(design_mod.PREVIEW_SKIP)}
        except Exception as e:
            preview = {"parse_error": f"{type(e).__name__}: {e}"}
        # ETL pipeline 建議檔（獨立產物；沒給資訊就長殼，缺的欄位進問答區）
        etl = etl_manifest.build(name, design_result, ctx_meta)
        etl_questions = etl_manifest.open_questions(name, etl, ctx_domains)
        # 正式區複用：設計稿有沒有引用已核准資產（確定性；沒有就進問答）
        design_reused = prodassets.referenced_by_design(design_result,
                                                        prod_assets)
        reuse_q = prodassets.open_question(name, prod_assets, design_reused)
        design_questions = list(etl_questions)
        if reuse_q:
            design_questions.append(
                {"question": reuse_q["question"],
                 "proposed_answer": reuse_q["answer"]})
        # 設計提問代填進 design_answers.yaml（只新增未覆蓋的題、不動既有條目；
        # 問答檔壞掉時不改寫，只提醒）
        proposed_added = 0
        if qa_problems:
            print(f"  🎨 {name}: design_answers.yaml 有問題，代填未寫入"
                  f"（請先修復：{'；'.join(qa_problems)}）")
        else:
            qa_data, proposed_added = design_mod.merge_design_answers(
                qa_data, (design_result.get("open_questions") or [])
                + design_questions)
            if proposed_added:
                with open(qa_path, "w", encoding="utf-8") as f:
                    f.write(design_mod.answers_to_yaml(qa_data, name))
        # 產品前綴：context 宣告 product 且已登錄 → 逐表檢查表名格式
        products = design_mod.load_products(CONFIG_DIR, ctx_domains)
        declared_code = str(ctx_meta.get("product") or "").strip().lower()
        product = None
        if declared_code:
            entry = products["codes"].get(declared_code) or {}
            product = {"code": declared_code, "name": entry.get("name", ""),
                       "layers": list(products["layers"])}
        index_entries = design_mod.design_index(CONFIG_DIR, ctx_domains)
        info = design_mod.render(
            name, design_result, ctx, ITERATIONS_ROOT, ddir,
            gate_preview=preview, answers=qa_data,
            config_sources=design_mod.reference_materials(
                CONFIG_DIR, ctx_domains),
            product=product,
            required_sources=[e["path"] for e in index_entries
                              if e["required"]],
            etl=etl)
        state = ("首稿" if info["first"] else
                 "已演進" if info["changed"] else "不變")
        # 🎨 設計 HTML 報告（與 🛡 治理報告是兩份不同的東西——視覺與定位
        # 都區隔；含 Logical／Physical 分區與素材足跡 mindmap）。
        # 最新版固定入口＋輪次戳記版各一份，與 govern 報告同一慣例。
        design_html = design_report.to_html(
            name, info["round"], design_result, state=state,
            gate_preview=preview, answers=qa_data, entries=index_entries,
            product=product, domains=ctx_domains,
            ddl_diff=info.get("ddl_diff", ""), files=info["files"], etl=etl)
        for fname in (f"{name}.design_report.html",
                      f"{name}.design_round_{info['round']}.report.html"):
            with open(os.path.join(ddir, fname), "w",
                      encoding="utf-8") as f:
                f.write(design_html)
        gate = ("預檢 " + ("✅ 合規" if preview.get("compliant") else "❌ 不合規")
                if "compliant" in preview else "預檢略過（草稿 DDL 解析失敗）")
        print(f"  🎨 {name}: design mode ｜ 第 {info['round']} 輪設計（{state}）"
              f"｜ {gate} → {dlabel}/{name}.design_report.html"
              f"（HTML 報告）、{name}.design_story.md（人讀）、"
              f"{name}.logical_design.md、"
              f"{name}.physical_design.md、{name}.design.sql"
              + (f"（DDL 拆檔 {info['ddl_files']} 份 → {name}.design/）"
                 if info.get("ddl_files") else ""))
        if prod_assets:
            print("     🏛 正式區複用："
                  + ("已引用 " + "、".join(f"`{h}`" for h in design_reused)
                     if design_reused else
                     f"⚠️ 未引用任何正式區資產（現有 {len(prod_assets)} 個已核准"
                     f"主體）——已列入設計問答，請交代原因或補上引用"))
        etl_info = etl_manifest.summary(etl)
        print(f"     🔧 ETL 建議檔：{dlabel}/{name}.etl.yaml"
              f"（pipeline 欄位已填 {etl_info['filled']}／"
              f"{etl_info['total']}）"
              + ("" if not etl_info["missing"] else
                 "——缺：" + "、".join(etl_info["missing"])
                 + f"，已在設計問答請使用者填（input/{name}/"
                   "design_answers.yaml）"))
        qa = design_mod.qa_state(qa_data)
        if qa["answered"] or qa["proposed"] or qa["deferred"]:
            print(f"     ❓ 設計問答：已答 {len(qa['answered'])}、"
                  f"待驗證 {len(qa['proposed'])}（本次代填 {proposed_added}）、"
                  f"擱置 {len(qa['deferred'])}"
                  + ("" if not qa["proposed"] else
                     f" → 驗證：input/{name}/design_answers.yaml"
                     "（proposed → answered／deferred）"))

    any_noncompliant = False
    any_precheck_failed = False
    advisory_pending: list[str] = []  # subjects whose 顧問區 still needs an agent LLM
    for ddl_path in ddls:
        name = os.path.splitext(os.path.basename(ddl_path))[0]
        gdir = docpaths.govern_dir(DOC_ROOT, name)
        glabel = docpaths.label(gdir, HERE)
        if precheck_mode == "legacy":
            case = load_input(ddl_path)
        else:
            # 前置檢核（存在 → 可解析 → 一致）。四件不齊就不產 report。
            pre = preflight.run_precheck(ddl_path)
            with open(os.path.join(gdir, name + ".precheck.md"),
                      "w", encoding="utf-8") as f:
                f.write(preflight.to_markdown(pre))
            for line in preflight.console_lines(pre):
                print("  " + line)
            if not pre.passed:
                any_precheck_failed = True
                print(f"     → 補齊後重跑；缺件明細見 "
                      f"{glabel}/{name}.precheck.md")
                continue
            case = load_input_v2(ddl_path, pre)
        # 正式區複用：沒引用任何已核准資產 → 確定性問答題（先寫再驗證，
        # 這輪的迭代統計就看得到；已覆蓋的主題不重複新增）。
        # legacy 模式是內部 fixtures（平鋪佈局、共用一份 answers），不寫。
        reuse_q = None if precheck_mode == "legacy" else prodassets.open_question(
            name, prod_assets,
            prodassets.referenced_by_relations(case.relations, prod_assets))
        if reuse_q and not case.answers_problems:
            from dataval import answers as answers_mod
            merged_answers, reuse_added = answers_mod.add_proposals(
                case.answers, [reuse_q])
            if reuse_added:
                # 注意：case.answers_file 只是顯示用檔名，路徑一律用 locate()
                answers_path = answers_mod.locate(ddl_path)
                with open(answers_path, "w", encoding="utf-8") as f:
                    f.write(answers_mod.answers_to_yaml(merged_answers, name))
                case.answers = merged_answers
                print(f"     🏛 正式區複用：⚠️ 未引用任何正式區資產"
                      f"（現有 {len(prod_assets)} 個已核准主體）"
                      f"——已列入問答：input/{name}/answers.yaml")
        schema, findings, meta = validate(
            case.ddl, cfg, sample_data=case.sample, context=case.context,
            business_keys=case.business_keys, lineage_spec=case.lineage,
            relations=case.relations, er_diagram=case.er_diagram,
            diagnostics=case.diagnostics, llm=llm,
            domain_root=DOMAIN_ROOT, rules_root=RULES_ROOT, domains=case.domains,
            config_dir=CONFIG_DIR, production_root=PRODUCTION_ROOT,
            answers=case.answers, answers_problems=case.answers_problems,
            answers_file=case.answers_file,
            derivation=case.derivation,
            derivation_problems=case.derivation_problems,
            derivation_file=case.derivation_file,
            table_files=case.table_files,
            # design → govern streamline：有設計歷史時建議 DDL 延續設計稿
            design_snapshot=design_mod.latest_round_result(
                ITERATIONS_ROOT, name))
        meta["case_config"] = case.config_source
        meta["validation_manifest"] = validation_manifest(ddl_path, compiled_path)
        # Backward-compatible display key. The value now covers declarative
        # rules, Python rules, built-in validators, and parser dependencies.
        meta["rule_version_code"] = meta["validation_manifest"][
            "validation_bundle_code"]

        # 迭代歷史：每輪快照＋input 變更＋建議演進（iterations/<名>/）。
        # 純報告層，不影響任何 finding。
        from dataval import iterations as iter_history
        s0 = summarize(findings)
        round_no = iter_history.record_full_round(
            ITERATIONS_ROOT, name, ddl_path, meta, findings,
            {"compliant": s0["compliant"], "fails": s0["fail"]})

        # HTML 永遠產生。未接 LLM 時顧問區會標示待補完，但所有確定性
        # checking rule ID、lineage 與合規判定仍可直接閱讀。
        outputs = {
            ".report.md": to_markdown(findings, meta),
            ".report.json": to_json(findings, meta),
            ".report.html": to_html(findings, meta),
        }
        write_report_outputs(name, round_no, outputs,
                             proposal=meta.get("ddl_proposal"))
        # 每輪報告存檔＋變更報告（只列有改動的地方）→ iterations/<名>/
        iter_history.archive_round_outputs(ITERATIONS_ROOT, name, round_no,
                                           outputs[".report.md"],
                                           meta["iteration"])

        # If Python has no LLM, export an advisory prompt for the opencode agent
        # to complete with ITS llm; agent writes <name>.advisory_result.json then
        # runs `python merge_advisory.py` to fill the advisory zone in the HTML.
        if not llm_on:
            pending = pending_advisory_specs(findings, compiled_path)
            from dataval import answers as answers_mod
            reuse_hits = prodassets.referenced_by_relations(case.relations,
                                                            prod_assets)
            prompt = build_advisory_prompt(
                schema, case.context,
                business_materials=design_mod.business_materials(
                    CONFIG_DIR, case.domains),
                production_assets=prodassets.advisory_material(
                    prod_assets,
                    prodassets.candidates(prodassets.schema_pairs(schema),
                                          prod_assets, reuse_hits),
                    reuse_hits),
                                           name=name, pending_skills=pending,
                                           unregistered_candidates=meta.get(
                                               "unregistered_candidates", []),
                                           clarified=answers_mod.clarified_text(
                                               case.answers),
                                           table_purposes=meta.get(
                                               "reference_purposes", {}),
                                           derivation=meta.get("derivation"))
            with open(os.path.join(gdir, name + ".advisory_prompt.md"),
                      "w", encoding="utf-8") as f:
                f.write(prompt)
            advisory_pending.append(name)

        s = summarize(findings)
        flag = "✅ 合規" if s["compliant"] else f"❌ 不合規（會擋 {s['blocking_count']}）"
        bs = blocking_summary(findings)
        if bs["blocked"]:
            rules = "、".join(b["rule"] for b in bs["blocked"])
            flag += f" ｜ 卡下來的規則：{rules}"
        any_noncompliant = any_noncompliant or not s["compliant"]
        dom_str = "、".join(meta.get("domains_loaded", [])) or "(無)"

        # 跑完 data governance 流程後，自動產生這個 data subject 的摘要與用途。
        # 放到 govern_doc/<名>/<名>.subject_summary.md，作為放入 production 前的說明。
        summary_md = build_summary(schema, meta.get("domains_loaded"),
                                   s["compliant"], llm)
        with open(os.path.join(gdir, name + ".subject_summary.md"),
                  "w", encoding="utf-8") as f:
            f.write(summary_md)

        print(f"  🛡 {name}: govern mode ｜ {flag} ｜ domain: {dom_str} → "
              f"{glabel}/{name}.report.html"
              f"（本輪存檔 {name}.round_{round_no}.report.*；"
              f"＋摘要 {name}.subject_summary.md）")
        overview = meta.get("table_overview") or []
        if len(overview) > 1:   # 多表 subject：逐表狀態一行看懂
            tcounts = table_finding_counts(findings,
                                           [r["table"] for r in overview])
            print("     📋 表：" + " ｜ ".join(
                f"{r['table']}（❌{tcounts[r['table'].lower()]['fail']}"
                f"/⚠️{tcounts[r['table'].lower()]['warning']}）"
                + (f" ← {r['file']}" if r.get("file") else "")
                for r in overview))
        ds = meta.get("design_sync") or {}
        if not ds.get("has_design"):
            print("     🎨 設計對照：未經過設計模式（手寫 DDL 直接進治理）")
        elif ds.get("identical"):
            print(f"     🎨 設計對照：與設計稿 第 {ds['design_round']} 輪"
                  "完全一致")
        else:
            print(f"     🎨 設計對照：與設計稿 第 {ds['design_round']} 輪"
                  "有差異（明細見報告「設計對照」區塊）")

        # 迭代問答狀態（每輪通知的一部分；詳見報告的「迭代收斂」區塊）
        it = meta.get("iteration") or {}
        if it:
            if it.get("converged"):
                state = "✅ 已收斂"
            elif it.get("advisory_pending"):
                state = ("待答題數待顧問區補完後確定"
                         f"（閘門 fail {it['blockers']['gating_fails']}）")
            else:
                state = (f"待答 {it['blockers']['open_questions']}、"
                         f"待驗證 {it['blockers'].get('proposed_unverified', 0)}、"
                         f"已解 {len(it.get('answered') or [])}、"
                         f"閘門 fail {it['blockers']['gating_fails']} → ❌ 未收斂")
            print(f"     ↻ 迭代 第 {it.get('round', 1)}/{it.get('max_rounds', 5)} 輪：{state}")
            if (it.get("round", 1) >= it.get("max_rounds", 5)
                    and not it.get("converged")):
                print("     ⚠️ 已達迭代上限，建議收斂問題範圍或人工決策。")

    print(f"完成。🎨 設計文件在 {design_root_label}/<主體>/、"
          f"🛡 治理報告在 {govern_root_label}/<主體>/。")
    if design_pending:
        # 寫給正在執行的 agent 看的待辦：design mode 的設計稿還沒起草，
        # agent 必須用自身 LLM 依 design_prompt 補上，設計產物才會出現。
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🎨  design mode 設計稿待產生——這些 subject 只有 context.md。")
        print(f"   待設計主題（{len(design_pending)} 個）："
              + "、".join(design_pending))
        print("")
        print("   👉 正在執行的 agent 請完成以下步驟（這是 design mode 的產出）：")
        for nm in design_pending:
            lbl = docpaths.label(docpaths.design_dir(DOC_ROOT, nm), HERE)
            print(f"     1. 讀 {lbl}/{nm}.design_prompt.md，依其格式與"
                  f" schema 產出 {lbl}/{nm}.design_result.json")
        print(f"     2. 重跑：python run.py "
              + " ".join(design_pending))
        print(f"   完成後 {design_root_label}/<主體>/ 會出現 logical_design.md、"
              "physical_design.md、design.sql、etl.yaml（設計輪次自動記錄）。")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if advisory_pending:
        # 這段是刻意寫給「正在跑 run.py 的 agent（opencode / Claude Code）」看的
        # 待辦指令：報告的顧問區尚未補完，agent 必須用自身 LLM 接著把它填完，
        # 否則交付的報告不完整（HTML 顧問區只會顯示「待補完」）。
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("⚠️  顧問區尚未補完——報告還不算完成。")
        print("   run.py 是零 LLM 的閘門區行程，語意建議需要 agent 用自身 LLM 補上。")
        print(f"   待補主題（{len(advisory_pending)} 個）："
              + "、".join(advisory_pending))
        print("")
        print("   👉 正在執行的 agent 請立刻完成以下步驟（這是輸出報告的一部分）：")
        for nm in advisory_pending:
            lbl = docpaths.label(docpaths.govern_dir(DOC_ROOT, nm), HERE)
            print(f"     1. 讀 {lbl}/{nm}.advisory_prompt.md，"
                  f"依其格式與 schema 產出 {lbl}/{nm}.advisory_result.json")
        print(f"     2. 執行：python merge_advisory.py")
        print(f"     3. 執行：python merge_advisory.py --status（exit 0 = 顧問區全數補完）")
        print("   完成後 HTML 顧問區才會顯示真實建議，而非「待補完」。")
        print("   （若本機另有直連 LLM，可改設 DATAVAL_LLM_BASE_URL 讓 run.py 直接填。）")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if any_precheck_failed:
        print("有 data subject 輸入不齊全，未產生報告。四件輸入格式見 "
              "input/README.md；缺件明細見 govern_doc/<名>/<名>.precheck.md。",
              file=sys.stderr)
        sys.exit(2)
    if strict and any_noncompliant:
        print("嚴格模式：存在不合規 DDL。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
