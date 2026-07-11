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
  - DataHub 依 config 設定，未接上則 bypass
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from dataval.engine import load_config, validate
from dataval.report import to_json, to_markdown, to_html, summarize, blocking_summary
from dataval.llm import from_env
from dataval.parser import parse_ddl
from dataval.advisory_export import build_advisory_prompt
from dataval.subject_summary import build_summary
from dataval.compiler import ensure_compiled

INPUT_DIR = os.path.join(HERE, "input")
REPORT_DIR = os.path.join(HERE, "reports")
CONFIG = os.path.join(HERE, "config", "default.yaml")
CONFIG_DIR = os.path.join(HERE, "config")
SKILLS_ROOT = os.path.join(HERE, "config", "skills")
SKILL_PY = os.path.join(HERE, "config", "skills_py")
PROMOTED_ROOT = os.path.join(HERE, "promoted")


def find_ddls() -> list[str]:
    if not os.path.isdir(INPUT_DIR):
        return []
    out = []
    for fn in sorted(os.listdir(INPUT_DIR)):
        if fn.lower().endswith((".sql", ".ddl")):
            out.append(os.path.join(INPUT_DIR, fn))
    return out


def sample_for(ddl_path: str):
    base = os.path.splitext(ddl_path)[0]
    for cand in (base + ".sample.json", base + ".samples.json"):
        if os.path.isfile(cand):
            try:
                return json.load(open(cand, encoding="utf-8"))
            except Exception:
                return None
    return None


def context_for(ddl_path: str) -> str:
    base = os.path.splitext(ddl_path)[0]
    ctx = base + ".context.txt"
    if os.path.isfile(ctx):
        return open(ctx, encoding="utf-8").read().strip()
    return ""


def domains_for(ddl_path: str) -> list | None:
    """Resolve which domains to load for this DDL.

    Priority:
      1. Per-DDL file  <name>.domains.yaml  (advanced: a described template)
      2. Shared template  input/_domains.yaml  (applies to all DDLs)
      3. [] -> 只載入 common（安全預設）

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
                spec = _yaml.safe_load(open(c, encoding="utf-8")) or {}
                doms = spec.get("domains")
                if isinstance(doms, list) and doms:
                    return [str(d) for d in doms]
            except Exception:
                pass
    return []


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
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
        ddl = open(ddl_path, encoding="utf-8").read()
        doms = domains_for(ddl_path)
        schema, findings, meta = validate(
            ddl, cfg, sample_data=sample_for(ddl_path),
            context=context_for(ddl_path), llm=llm,
            skills_root=SKILLS_ROOT, skill_py_dir=SKILL_PY, domains=doms,
            config_dir=CONFIG_DIR, promoted_root=PROMOTED_ROOT)

        md_path = os.path.join(REPORT_DIR, name + ".report.md")
        js_path = os.path.join(REPORT_DIR, name + ".report.json")
        html_path = os.path.join(REPORT_DIR, name + ".report.html")
        open(md_path, "w", encoding="utf-8").write(to_markdown(findings, meta))
        open(js_path, "w", encoding="utf-8").write(to_json(findings, meta))
        if llm_on:
            # 顧問區已由本地 LLM 填完 → 直接產完成版 HTML
            open(html_path, "w", encoding="utf-8").write(to_html(findings, meta))
        else:
            # 未接本地 LLM：HTML 等 agent 補完建議後由 merge_advisory.py 產生，
            # 使用者看到的 HTML 永遠是兩區皆有真實內容的完成版。
            if os.path.exists(html_path):
                os.remove(html_path)

        # If Python has no LLM, export an advisory prompt for the opencode agent
        # to complete with ITS llm; agent writes <name>.advisory_result.json then
        # runs `python merge_advisory.py` to fill the advisory zone in the HTML.
        if not llm_on:
            schema_only = parse_ddl(ddl, sample_data=sample_for(ddl_path),
                                    context=context_for(ddl_path))
            pending = [{"id": f.check_id.replace("SKILL.", ""),
                        "title": f.message.split("「")[-1].split("」")[0] if "「" in f.message else f.check_id,
                        "desc": "見 skill 描述"}
                       for f in findings
                       if f.zone == "advisory" and "略過語意卡控" in f.message]
            prompt = build_advisory_prompt(schema_only, context_for(ddl_path),
                                           name=name, pending_skills=pending)
            open(os.path.join(REPORT_DIR, name + ".advisory_prompt.md"),
                 "w", encoding="utf-8").write(prompt)

        s = summarize(findings)
        flag = "✅ 合規" if s["compliant"] else f"❌ 不合規（會擋 {s['blocking_count']}）"
        bs = blocking_summary(findings)
        if bs["blocked"]:
            rules = "、".join(b["rule"] for b in bs["blocked"])
            flag += f" ｜ 卡下來的規則：{rules}"
        any_noncompliant = any_noncompliant or not s["compliant"]
        dom_str = "、".join(meta.get("domains_loaded", [])) or "(無)"

        # 跑完 data governance 流程後，自動產生這個 data subject 的摘要與用途。
        # 放到 reports/<名>.subject_summary.md，作為放入正式區前的說明文件。
        schema_for_sum = parse_ddl(ddl, sample_data=sample_for(ddl_path),
                                   context=context_for(ddl_path))
        summary_md = build_summary(schema_for_sum, meta.get("domains_loaded"),
                                   s["compliant"], llm)
        open(os.path.join(REPORT_DIR, name + ".subject_summary.md"),
             "w", encoding="utf-8").write(summary_md)

        print(f"  {name}: {flag} ｜ domain: {dom_str} → reports/{name}.report.md"
              f"（＋摘要 {name}.subject_summary.md）")

    print("完成。報告在 reports/ 資料夾。")
    if not llm_on:
        print("（未接本地 LLM：HTML 尚未產生。agent 依 *.advisory_prompt.md 產出"
              " advisory_result.json 後跑 python merge_advisory.py，"
              "屆時的 HTML 兩區皆為真實內容。）")


if __name__ == "__main__":
    main()
