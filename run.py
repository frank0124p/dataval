#!/usr/bin/env python3
"""零參數自動執行：掃 input/ 下所有 DDL，逐一驗證並把報告寫到 reports/。

用法（在專案根目錄）：
    python run.py

行為：
  - 自動找 input/ 裡的 *.sql / *.ddl
  - 若同名的 *.sample.json 存在（例如 orders.sql ↔ orders.sample.json）會自動帶入
  - 自動載入 config/skills 與 config/skills_py 裡的 skill
  - 每個 DDL 產生 reports/<名稱>.report.md 與 .report.json
  - LLM 看環境變數 DATAVAL_LLM_BASE_URL；沒設就只跑閘門區（仍能出合規判定）
"""
from __future__ import annotations
import json
import os
import sys
from dataclasses import dataclass

from dataval.engine import load_config, validate
from dataval.report import to_json, to_markdown, to_html, summarize, blocking_summary
from dataval.llm import from_env
from dataval.advisory_export import build_advisory_prompt
from dataval.subject_summary import build_summary
from dataval.compiler import ensure_compiled
from dataval.model import Finding, ZONE_GATING

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.environ.get("DATAVAL_INPUT_DIR", os.path.join(HERE, "input"))
REPORT_DIR = os.environ.get("DATAVAL_REPORT_DIR", os.path.join(HERE, "reports"))
CONFIG = os.path.join(HERE, "config", "default.yaml")
CONFIG_DIR = os.path.join(HERE, "config")
SKILLS_ROOT = os.path.join(HERE, "config", "skills")
SKILL_PY = os.path.join(HERE, "config", "skills_py")
PRODUCTION_ROOT = os.path.join(HERE, "production")


@dataclass
class InputCase:
    ddl: str
    sample: dict | None
    context: str
    domains: list[str]
    business_keys: dict[str, list[str]]
    lineage: dict | None
    diagnostics: list[Finding]


def find_ddls() -> list[str]:
    if not os.path.isdir(INPUT_DIR):
        return []
    out = []
    for fn in sorted(os.listdir(INPUT_DIR)):
        if fn.lower().endswith((".sql", ".ddl")):
            out.append(os.path.join(INPUT_DIR, fn))
    return out


def _input_diagnostic(check_id: str, target: str, message: str,
                      *, blocking: bool = False) -> Finding:
    return Finding(check_id, "structural", "fail" if blocking else "warning",
                   target, message, severity="error" if blocking else "warning",
                   source="rule", zone=ZONE_GATING,
                   expected="companion 檔案可正確讀取與解析",
                   actual=message, fix=f"修正檔案 {target}")


def sample_for(ddl_path: str, diagnostics: list[Finding] | None = None):
    base = os.path.splitext(ddl_path)[0]
    for cand in (base + ".sample.json", base + ".samples.json"):
        if os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                if diagnostics is not None:
                    diagnostics.append(_input_diagnostic(
                        "SYSTEM.SAMPLE_PARSE", cand,
                        f"樣本 JSON 解析失敗：{type(e).__name__}: {e}"))
                return None
    return None


def context_for(ddl_path: str, diagnostics: list[Finding] | None = None) -> str:
    base = os.path.splitext(ddl_path)[0]
    ctx = base + ".context.txt"
    if os.path.isfile(ctx):
        try:
            with open(ctx, encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            if diagnostics is not None:
                diagnostics.append(_input_diagnostic(
                    "SYSTEM.CONTEXT_READ", ctx,
                    f"情境檔讀取失敗：{type(e).__name__}: {e}"))
    return ""


def domains_for(ddl_path: str, diagnostics: list[Finding] | None = None) -> list:
    """Resolve which domains to load for this DDL.

    Priority:
      1. Per-DDL file  <name>.domains.yaml  (advanced: a described template)
      2. Shared template  input/_domains.yaml  (applies to all DDLs)
      3. [] -> 只載入 Common（安全預設）

    Template format (either file):
        domains: [PLM, FCM]      # which domains this design relates to
        # description is free text for humans/agent; not parsed for logic
        description: |
          這份設計屬於 PLM 的料件主檔，並與 FCM 的主檔有關聯。
    """
    import yaml as _yaml
    base = os.path.splitext(ddl_path)[0]
    candidates = [base + ".domains.yaml", base + ".domains.yml",
                  os.path.join(INPUT_DIR, "_domains.yaml"),
                  os.path.join(INPUT_DIR, "_domains.yml")]
    for c in candidates:
        if os.path.isfile(c):
            try:
                with open(c, encoding="utf-8") as f:
                    spec = _yaml.safe_load(f) or {}
                doms = spec.get("domains")
                if isinstance(doms, list) and doms:
                    return [str(d) for d in doms]
                if diagnostics is not None:
                    diagnostics.append(_input_diagnostic(
                        "SYSTEM.DOMAIN_SPEC", c,
                        "domain YAML 必須含非空的 domains list"))
            except Exception as e:
                if diagnostics is not None:
                    diagnostics.append(_input_diagnostic(
                        "SYSTEM.DOMAIN_SPEC", c,
                        f"domain YAML 解析失敗：{type(e).__name__}: {e}"))
            return []
    return []


def keys_for(ddl_path: str, diagnostics: list[Finding] | None = None) -> dict[str, list[str]]:
    import yaml as _yaml
    base = os.path.splitext(ddl_path)[0]
    candidates = [base + ".keys.yaml", base + ".keys.yml"]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                spec = _yaml.safe_load(f) or {}
            keys = spec.get("business_keys")
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
                    "SYSTEM.BUSINESS_KEY_SPEC", path,
                    f"business key YAML 解析失敗：{type(e).__name__}: {e}",
                    blocking=True))
            return {}
    return {}


def lineage_for(ddl_path: str, diagnostics: list[Finding] | None = None) -> dict | None:
    """Load optional explicit design-lineage metadata for one DDL."""
    import yaml as _yaml
    base = os.path.splitext(ddl_path)[0]
    for path in (base + ".lineage.yaml", base + ".lineage.yml"):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                spec = _yaml.safe_load(f)
            if not isinstance(spec, dict):
                raise ValueError("lineage companion 根節點必須是 mapping")
            return spec
        except Exception as e:
            if diagnostics is not None:
                diagnostics.append(_input_diagnostic(
                    "SYSTEM.LINEAGE_SPEC", path,
                    f"lineage YAML 解析失敗：{type(e).__name__}: {e}",
                    blocking=True))
            # Empty dict means a companion exists but is invalid. This avoids
            # turning a broken declaration into a non-blocking suggestion.
            return {}
    return None


def load_input(ddl_path: str) -> InputCase:
    """Read one DDL and all of its optional companion files once."""
    diagnostics: list[Finding] = []
    try:
        with open(ddl_path, encoding="utf-8") as f:
            ddl = f.read()
    except Exception as e:
        ddl = ""
        diagnostics.append(_input_diagnostic(
            "SYSTEM.DDL_READ", ddl_path,
            f"DDL 讀取失敗：{type(e).__name__}: {e}", blocking=True))
    return InputCase(
        ddl=ddl,
        sample=sample_for(ddl_path, diagnostics),
        context=context_for(ddl_path, diagnostics),
        domains=domains_for(ddl_path, diagnostics),
        business_keys=keys_for(ddl_path, diagnostics),
        lineage=lineage_for(ddl_path, diagnostics),
        diagnostics=diagnostics,
    )


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
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_dir_label = os.path.relpath(REPORT_DIR, HERE)
    ddls = find_ddls()
    if not ddls:
        print(f"找不到 DDL。請把 .sql 或 .ddl 檔放進：{INPUT_DIR}")
        sys.exit(0)

    cfg = load_config(CONFIG)

    # 規則 compile：每次重建結構化內容，有變更才寫入 JSON。
    compiled_path, recompiled = ensure_compiled(
        SKILLS_ROOT, SKILL_PY, os.path.join(HERE, "build", "compiled_rules.json"))
    print(("規則有更新 → 已重新 compile：" if recompiled else "規則未變 → 沿用既有 compile：")
          + os.path.relpath(compiled_path, HERE))
    llm = from_env()
    llm_on = type(llm).__name__ != "NullLLM"

    print(f"找到 {len(ddls)} 個 DDL；LLM：{'已接' if llm_on else '未接（只跑閘門區）'}")
    any_noncompliant = False
    for ddl_path in ddls:
        name = os.path.splitext(os.path.basename(ddl_path))[0]
        case = load_input(ddl_path)
        schema, findings, meta = validate(
            case.ddl, cfg, sample_data=case.sample, context=case.context,
            business_keys=case.business_keys, lineage_spec=case.lineage,
            diagnostics=case.diagnostics, llm=llm,
            skills_root=SKILLS_ROOT, skill_py_dir=SKILL_PY, domains=case.domains,
            config_dir=CONFIG_DIR, production_root=PRODUCTION_ROOT)

        md_path = os.path.join(REPORT_DIR, name + ".report.md")
        js_path = os.path.join(REPORT_DIR, name + ".report.json")
        html_path = os.path.join(REPORT_DIR, name + ".report.html")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(to_markdown(findings, meta))
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(to_json(findings, meta))
        if llm_on:
            # 顧問區已由本地 LLM 填完 → 直接產完成版 HTML
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(to_html(findings, meta))
        else:
            # 未接本地 LLM：HTML 等 agent 補完建議後由 merge_advisory.py 產生，
            # 使用者看到的 HTML 永遠是兩區皆有真實內容的完成版。
            if os.path.exists(html_path):
                os.remove(html_path)

        # If Python has no LLM, export an advisory prompt for the opencode agent
        # to complete with ITS llm; agent writes <name>.advisory_result.json then
        # runs `python merge_advisory.py` to fill the advisory zone in the HTML.
        if not llm_on:
            pending = pending_advisory_specs(findings, compiled_path)
            prompt = build_advisory_prompt(schema, case.context,
                                           name=name, pending_skills=pending,
                                           unregistered_candidates=meta.get(
                                               "unregistered_candidates", []))
            with open(os.path.join(REPORT_DIR, name + ".advisory_prompt.md"),
                      "w", encoding="utf-8") as f:
                f.write(prompt)

        s = summarize(findings)
        flag = "✅ 合規" if s["compliant"] else f"❌ 不合規（會擋 {s['blocking_count']}）"
        bs = blocking_summary(findings)
        if bs["blocked"]:
            rules = "、".join(b["rule"] for b in bs["blocked"])
            flag += f" ｜ 卡下來的規則：{rules}"
        any_noncompliant = any_noncompliant or not s["compliant"]
        dom_str = "、".join(meta.get("domains_loaded", [])) or "(無)"

        # 跑完 data governance 流程後，自動產生這個 data subject 的摘要與用途。
        # 放到 reports/<名>.subject_summary.md，作為放入 production 前的說明文件。
        summary_md = build_summary(schema, meta.get("domains_loaded"),
                                   s["compliant"], llm)
        with open(os.path.join(REPORT_DIR, name + ".subject_summary.md"),
                  "w", encoding="utf-8") as f:
            f.write(summary_md)

        print(f"  {name}: {flag} ｜ domain: {dom_str} → "
              f"{report_dir_label}/{name}.report.md"
              f"（＋摘要 {name}.subject_summary.md）")

    print(f"完成。報告在 {report_dir_label}/ 資料夾。")
    if not llm_on:
        print("（未接本地 LLM：HTML 尚未產生。agent 依 *.advisory_prompt.md 產出"
              " advisory_result.json 後跑 python merge_advisory.py，"
              "屆時的 HTML 兩區皆為真實內容。）")
    if strict and any_noncompliant:
        print("嚴格模式：存在不合規 DDL。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
