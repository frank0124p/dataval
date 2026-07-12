"""Engine: orchestrates the full pipeline from the architecture diagram.

Stations: parse -> skill load -> check engine (4 cats) -> [split gating/advisory]
-> DataHub station -> report. Concept layer runs in the advisory zone.

Core architectural rule enforced here:
  Any finding from an LLM source is FORCED to the advisory zone and info severity,
  so it can never affect the compliance verdict. Rule/skill findings stay gating.
"""
from __future__ import annotations
import os
import yaml
from .parser import parse_ddl
from .model import Finding, ZONE_GATING, ZONE_ADVISORY
from .llm import LLMClient, NullLLM
from .skills import COMMON_DOMAIN, SkillRegistry
from . import datahub, concept, lineage, production, subject_inference


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_glossary(config_dir: str) -> dict:
    path = os.path.join(config_dir, "glossary.yaml")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _enforce_zone(f: Finding) -> Finding:
    """Enforce the hard gating/advisory boundary.

    Rule (structural, not just convention): anything that is LLM-derived OR
    already marked advisory is forced into the advisory zone and demoted to info,
    so it can NEVER contribute to the compliance verdict. Only deterministic
    rule/skill findings remain in the gating zone. This is what guarantees the
    gating result is reproducible: no LLM output can leak into it.
    """
    is_llm = (f.source == "llm")
    is_advisory = (f.zone == ZONE_ADVISORY)
    if is_llm or is_advisory:
        f.zone = ZONE_ADVISORY
        # advisory never blocks: collapse any fail/warning to info
        if f.status in ("fail", "warning"):
            f.status = "info"
        f.severity = "info"
        if f.source != "skill":   # keep skill provenance; otherwise mark llm
            f.source = "llm" if is_llm else f.source
    else:
        f.zone = ZONE_GATING
    return f


def validate(ddl: str, cfg: dict, dialect: str = "clickhouse",
             sample_data: dict | None = None, context: str = "",
             business_keys: dict[str, list[str]] | None = None,
             lineage_spec: dict | None = None,
             diagnostics: list[Finding] | None = None,
             llm: LLMClient | None = None,
             skills_root: str = "", skill_py_dir: str = "",
             domains: list[str] | None = None,
             config_dir: str = "config", production_root: str = "production"):
    llm = llm or NullLLM()
    business_keys = business_keys or {}
    schema = parse_ddl(ddl, dialect=dialect, sample_data=sample_data, context=context,
                       business_keys=business_keys)
    glossary = load_glossary(config_dir)

    # 規則 build 整合進主流程：先產生結構化的 compiled JSON，
    # 內容有變更才寫入，再「從 compiled JSON 載入」規則來執行。
    # .md 是撰寫格式；build/compiled_rules.json 是執行格式（單一執行來源）。
    from .compiler import ensure_compiled
    build_dir = os.path.join(os.path.dirname(os.path.abspath(config_dir)), "build")
    os.makedirs(build_dir, exist_ok=True)
    compiled_path, _ = ensure_compiled(
        skills_root, skill_py_dir,
        os.path.join(build_dir, "compiled_rules.json"))

    findings: list[Finding] = list(diagnostics or [])
    # 規則只有一個家：全部經由 compiled JSON 載入執行。
    # 確定性規則進閘門；```check-llm 進顧問。閘門路徑零 LLM。
    reg = SkillRegistry()
    reg.load_compiled(compiled_path, domains=domains, config_dir=config_dir)
    findings += reg.run(schema, llm, glossary, cfg)
    domains_loaded = reg.loaded_domains

    # Business key metadata is explicit and independently validated. A sorting
    # key or ClickHouse PRIMARY KEY never silently becomes a business key.
    key_errors: list[Finding] = []
    for table_name, keys in sorted(business_keys.items()):
        table = schema.table(table_name)
        if table is None:
            key_errors.append(Finding(
                "BUSINESS_KEY.METADATA", "structural", "fail", table_name,
                f"Business key metadata 指向不存在的表 '{table_name}'。",
                severity="error", source="rule", zone=ZONE_GATING,
                expected="metadata 表名存在於 DDL", actual="DDL 無此表",
                fix="修正 <DDL名>.keys.yaml 的表名"))
            continue
        missing = [key for key in keys if table.col(str(key)) is None]
        if missing:
            key_errors.append(Finding(
                "BUSINESS_KEY.METADATA", "structural", "fail", table_name,
                f"Business key metadata 含不存在欄位 {missing}。",
                severity="error", source="rule", zone=ZONE_GATING,
                expected="business key 欄位存在於表", actual=f"缺少 {missing}",
                fix="修正 keys.yaml 或補上 DDL 欄位"))
    if key_errors:
        findings += key_errors
    elif business_keys:
        findings.append(Finding(
            "BUSINESS_KEY.METADATA", "structural", "pass", "(schema)",
            f"Business key metadata 已驗證：{sorted(business_keys)}。",
            severity="info", source="rule", zone=ZONE_GATING))
    else:
        findings.append(Finding(
            "BUSINESS_KEY.METADATA", "structural", "skipped", "(schema)",
            "未提供 <DDL名>.keys.yaml，無法確認 business key。",
            severity="info", source="rule", zone=ZONE_GATING))

    # Domain scope is an explicit checking result. Missing selection is safe:
    # only Common runs, and the report warns instead of silently loading all.
    if reg.unknown_domains:
        findings.append(Finding(
            "DOMAIN.SCOPE", "structural", "warning", "(domains)",
            f"未知 domain：{reg.unknown_domains}；已略過，本次載入 {domains_loaded}。",
            severity="warning", source="rule", zone=ZONE_GATING,
            expected="domain 存在於 config/skills/<domain>",
            actual=f"未知 {reg.unknown_domains}",
            fix="修正 domains.yaml 名稱或建立對應 domain 目錄"))
    elif not reg.requested_domains:
        findings.append(Finding(
            "DOMAIN.SCOPE", "structural", "warning", "(domains)",
            f"未指定 domain，依安全預設只載入 {COMMON_DOMAIN}。",
            severity="warning", source="rule", zone=ZONE_GATING,
            expected="以 <DDL名>.domains.yaml 明確指定業務 domain",
            actual="未指定", fix="新增 domains.yaml；若確定只需共用規則可保持現狀"))
    else:
        findings.append(Finding(
            "DOMAIN.SCOPE", "structural", "pass", "(domains)",
            f"Domain 範圍已明確：{domains_loaded}。",
            severity="info", source="rule", zone=ZONE_GATING))

    # advisory concept layer (subject correctness)
    findings += concept.run(schema, llm)

    # Production baseline: selected domains reference approved DDL naming.
    findings += production.run(
        schema, production_root, domains_loaded, dialect, glossary)

    # Design lineage is explicit governance metadata. Declared relationships
    # are deterministic gating checks; absent metadata yields advisory hints.
    lineage_findings, lineage_meta = lineage.run(
        schema, lineage_spec, domains_loaded, production_root, dialect)
    findings += lineage_findings

    # SSOT 未登錄主體推斷 — 確定性啟發層（警告放行）。候選清單供顧問區產草稿。
    inf_findings, unreg_candidates = subject_inference.run(schema, cfg, glossary)
    findings += inf_findings

    # DataHub station (bypass in MVP)
    dh_findings, dh_state = datahub.run(schema, cfg)
    findings += dh_findings

    findings = [_enforce_zone(f) for f in findings]

    # Deterministic ordering so the same input always yields byte-identical
    # report bodies (excluding the timestamp). Sort by a stable key.
    findings.sort(key=lambda f: (f.category, f.zone, f.check_id, f.target,
                                 f.status, f.message))

    meta = {"dialect": dialect, "tables": len(schema.tables),
            "datahub_state": dh_state,
            "skills_loaded": reg.count(),
            "domains_loaded": reg.loaded_domains,
            "domains_requested": reg.requested_domains,
            "domains_unknown": reg.unknown_domains,
            "checking_rule_ids_loaded": reg.loaded_rule_ids,
            "lineage": lineage_meta,
            "unregistered_candidates": unreg_candidates}
    return schema, findings, meta
