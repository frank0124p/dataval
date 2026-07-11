#!/usr/bin/env python3
"""CLI for the dataval MVP.

Example:
  python -m dataval.cli \
    --ddl my_schema.sql \
    --config config/default.yaml \
    --sample samples.json \
    --context "新增 subscription 主體，跨 CRM 與 billing" \
    --out-json report.json --out-md report.md

LLM (company self-hosted, opencode) via env vars:
  DATAVAL_LLM_BASE_URL  DATAVAL_LLM_MODEL  DATAVAL_LLM_API_KEY
If unset, advisory zone is skipped; gating verdict is unaffected.
"""
from __future__ import annotations
import argparse
import json
import sys
from .engine import load_config, validate
from .report import to_json, to_markdown, to_html, summarize
from .llm import from_env


def main(argv=None):
    p = argparse.ArgumentParser(description="資料設計驗證 MVP")
    p.add_argument("--ddl", required=True)
    p.add_argument("--config", default="config/default.yaml")
    p.add_argument("--dialect", default="clickhouse")
    p.add_argument("--sample", default=None)
    p.add_argument("--keys", default=None,
                   help="Business key YAML：business_keys: {table: [column]}")
    p.add_argument("--context", default="")
    p.add_argument("--skills-root", default="config/skills")
    p.add_argument("--skill-py-dir", default="config/skills_py")
    p.add_argument("--domains", default="",
                   help="逗號分隔的 domain，例如 PLM,FCM；留空只載入 common；* 代表全部")
    p.add_argument("--out-json", default=None)
    p.add_argument("--out-md", default=None)
    p.add_argument("--out-html", default=None)
    p.add_argument("--strict", action="store_true",
                   help="不合規時以非零碼結束")
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    with open(args.ddl, encoding="utf-8") as f:
        ddl = f.read()
    if args.sample:
        with open(args.sample, encoding="utf-8") as f:
            sample = json.load(f)
    else:
        sample = None
    if args.keys:
        import yaml
        with open(args.keys, encoding="utf-8") as f:
            key_spec = yaml.safe_load(f) or {}
        business_keys = key_spec.get("business_keys") or {}
    else:
        business_keys = {}
    llm = from_env()
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]

    schema, findings, meta = validate(
        ddl, cfg, dialect=args.dialect, sample_data=sample,
        context=args.context, business_keys=business_keys, llm=llm,
        skills_root=args.skills_root, skill_py_dir=args.skill_py_dir,
        domains=domains)

    js = to_json(findings, meta)
    md = to_markdown(findings, meta)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            f.write(js)
    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as f:
            f.write(md)
    if args.out_html:
        with open(args.out_html, "w", encoding="utf-8") as f:
            f.write(to_html(findings, meta))
    if not args.out_json and not args.out_md and not args.out_html:
        print(md)

    s = summarize(findings)
    print(f"\n[摘要] 合規={s['compliant']} 會擋={s['blocking_count']} "
          f"閘門={s['gating']} 顧問={s['advisory']} "
          f"DataHub={meta.get('datahub_state')}", file=sys.stderr)
    if args.strict and not s["compliant"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
