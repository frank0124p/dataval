#!/usr/bin/env python3
"""把 agent 補完的顧問區建議合併進報告（含 HTML）。

用法（agent 產生 reports/<名>.advisory_result.json 後執行）：
    python merge_advisory.py

它會：
  1. 重跑每個 input/ DDL 的 gating 檢查（確保每條 checking rule ID 的閘門結果不變）。
  2. 讀 reports/<名>.advisory_result.json，把 agent 產生的建議轉成顧問區 findings。
  3. 重繪 reports/<名>.report.{md,json,html}，顧問區顯示真實建議。

閘門區完全不受影響（agent 的建議一律進顧問區、標 info、永不擋）。
"""
from __future__ import annotations
import argparse
import json
import os
import sys

from dataval.engine import load_config, validate
from dataval.report import to_json, to_markdown, to_html, summarize
from dataval.model import Finding, ZONE_ADVISORY
from dataval.llm import NullLLM
from dataval.advisory_export import validate_advisory_result
from dataval import answers as answers_mod
from dataval import design as design_mod

import run as R  # reuse paths + the single DDL/case-config loader


def _load_case(ddl_path: str):
    """Use the same strict/legacy input contract as run.py."""
    mode = os.environ.get("DATAVAL_PRECHECK", "strict").strip().lower()
    if mode == "legacy":
        return R.load_input(ddl_path)
    pre = R.preflight.run_precheck(ddl_path)
    if not pre.passed:
        details = "；".join(item.detail for item in pre.items if not item.ok)
        raise ValueError(f"四件輸入未通過前置檢核：{details}")
    return R.load_input_v2(ddl_path, pre)


def _advisory_complete(report_path: str) -> tuple[bool, str]:
    if not os.path.isfile(report_path):
        return False, "缺 report.json"
    try:
        with open(report_path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as error:
        return False, f"report.json 無法讀取：{error}"
    if (payload.get("meta") or {}).get("advisory_merged"):
        return True, "已由 agent 合併"
    findings = (payload.get("advisory_zone") or {}).get("findings")
    if not isinstance(findings, list):
        return False, "報告缺 advisory_zone.findings"
    pending = [finding for finding in findings
               if finding.get("status") == "skipped" and
               finding.get("source") == "llm"]
    if pending:
        return False, f"仍有 {len(pending)} 項語意檢查待補"
    return True, "顧問區沒有待補項目"


def status(ddls: list[str]) -> int:
    incomplete = 0
    for ddl_path in ddls:
        name = os.path.splitext(os.path.basename(ddl_path))[0]
        complete, detail = _advisory_complete(
            os.path.join(R.REPORT_DIR, name + ".report.json"))
        print(f"  {'✅' if complete else '❌'} {name}: {detail}")
        incomplete += 0 if complete else 1
    if not ddls:
        print("找不到任何 DDL。")
        return 1
    if incomplete:
        print(f"❌ {incomplete} 份報告的顧問區尚未完成。")
        return 1
    print("✅ 所有報告的顧問區均已完成。")
    return 0


def _canonical_gating(items: list[dict]) -> list[str]:
    """Direct, hash-free comparison form for complete gating findings."""
    return sorted(json.dumps(item, ensure_ascii=False, sort_keys=True)
                  for item in items)


def _gating_from_report(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    items = (payload.get("gating_zone") or {}).get("findings")
    if not isinstance(items, list):
        raise ValueError("報告缺少 gating_zone.findings")
    return _canonical_gating(items)


def _gating_from_findings(findings: list[Finding]) -> list[str]:
    return _canonical_gating([f.to_dict() for f in findings if f.zone == "gating"])


def _advisory_from_result(result: dict) -> list[Finding]:
    out: list[Finding] = []
    def mk(check_id, items):
        for it in (items or []):
            out.append(Finding(check_id, "naming" if "naming" in check_id else "concept",
                               "info", str(it.get("target", "(schema)")),
                               str(it.get("message", "")), severity="info",
                               rationale=str(it.get("rationale", "")),
                               source="llm", zone=ZONE_ADVISORY))
    mk("NAME.SEMANTIC", result.get("naming_semantic"))
    mk("CONCEPT.SUBJECT", result.get("concept"))
    for sid, items in (result.get("skills") or {}).items():
        for it in items:
            out.append(Finding(f"SKILL.{sid}", "best_practice", "info",
                               str(it.get("target", "(schema)")),
                               str(it.get("message", "")), severity="info",
                               rationale=str(it.get("rationale", "")),
                               source="llm", zone=ZONE_ADVISORY))
    return out


def _proposals_from_result(result: dict) -> list[dict]:
    """從 advisory_result 取出 agent 代填的答案（proposed_answer 欄位）。
    section → checking rule ID 的對應與 _advisory_from_result 完全一致。"""
    proposals: list[dict] = []

    def collect(check_id, items):
        for it in (items or []):
            answer = str(it.get("proposed_answer") or "").strip()
            if not answer:
                continue
            proposals.append({
                "id": f"{check_id}@{it.get('target', '(schema)')}",
                "question": str(it.get("message") or "").strip(),
                "answer": answer,
                "kind": str(it.get("proposed_kind") or "semantic"),
                "applied_to": str(it.get("proposed_applied_to") or "").strip(),
            })

    collect("NAME.SEMANTIC", result.get("naming_semantic"))
    collect("CONCEPT.SUBJECT", result.get("concept"))
    for sid, items in (result.get("skills") or {}).items():
        collect(f"SKILL.{sid}", items)
    return proposals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true",
                        help="只檢查所有報告的顧問區是否已補完")
    parser.add_argument("subjects", nargs="*",
                        help="只處理指定 subject（與 run.py 同寫法；空＝全部）")
    args = parser.parse_args()
    cfg = load_config(R.CONFIG)
    ddls = R.find_ddls()
    ddls, unknown = R.select_subjects(ddls, args.subjects)
    if unknown:
        print(f"找不到指定的 subject：{'、'.join(unknown)}", file=sys.stderr)
        sys.exit(1)
    if args.status:
        sys.exit(status(ddls))
    merged = 0
    guard_failed = 0
    for ddl_path in ddls:
        name = os.path.splitext(os.path.basename(ddl_path))[0]
        result_path = os.path.join(R.REPORT_DIR, name + ".advisory_result.json")
        if not os.path.isfile(result_path):
            continue
        try:
            with open(result_path, encoding="utf-8") as f:
                result = json.load(f)
        except Exception as e:
            print(f"  {name}: 讀取 advisory_result 失敗（{e}），略過")
            guard_failed += 1
            continue
        schema_errors = validate_advisory_result(result)
        if schema_errors:
            print(f"  {name}: advisory_result 不符合 "
                  "config/_engine/advisory_result.schema.json")
            for error in schema_errors:
                print(f"    - {error}")
            guard_failed += 1
            continue

        try:
            case = _load_case(ddl_path)
        except Exception as error:
            print(f"  {name}: 無法依目前輸入契約載入（{error}），停止合併")
            guard_failed += 1
            continue
        report_path = os.path.join(R.REPORT_DIR, name + ".report.json")
        try:
            previous_gating = _gating_from_report(report_path)
        except Exception as e:
            print(f"  {name}: 無法讀取合併前閘門結果（{e}），停止合併")
            guard_failed += 1
            continue

        # 重跑（NullLLM）取得穩定的 gating findings，再把 agent 建議加進顧問區
        schema, findings, meta = validate(
            case.ddl, cfg, sample_data=case.sample, context=case.context,
            business_keys=case.business_keys, lineage_spec=case.lineage,
            relations=case.relations,
            er_diagram=case.er_diagram,
            diagnostics=case.diagnostics, llm=NullLLM(),
            domain_root=R.DOMAIN_ROOT, rules_root=R.RULES_ROOT,
            domains=case.domains,
            config_dir=R.CONFIG_DIR, production_root=R.PRODUCTION_ROOT,
            answers=case.answers, answers_problems=case.answers_problems,
            answers_file=case.answers_file,
            derivation=case.derivation,
            derivation_problems=case.derivation_problems,
            derivation_file=case.derivation_file,
            design_snapshot=design_mod.latest_round_result(
                R.ITERATIONS_ROOT, name))
        meta["case_config"] = case.config_source
        compiled_path = os.path.join(R.HERE, "build", "compiled_rules.json")
        meta["validation_manifest"] = R.validation_manifest(ddl_path, compiled_path)
        meta["rule_version_code"] = meta["validation_manifest"][
            "validation_bundle_code"]

        current_gating = _gating_from_findings(findings)
        if current_gating != previous_gating:
            before_ids = sorted(json.loads(x)["check_id"] for x in previous_gating)
            after_ids = sorted(json.loads(x)["check_id"] for x in current_gating)
            print(f"  {name}: 閘門保護失敗，合併前後 checking rule 結果不同，已停止寫入")
            print(f"    合併前 rule IDs：{before_ids}")
            print(f"    重跑後 rule IDs：{after_ids}")
            guard_failed += 1
            continue

        # 移除「待補完」佔位（未接 LLM 的 info 佔位），換成 agent 的真實建議
        placeholder_ids = {"NAME.SEMANTIC", "CONCEPT.SKIPPED", "BP.LLM", "SSOT.LLM"}
        findings = [f for f in findings
                    if not (f.zone == ZONE_ADVISORY and
                            (f.check_id in placeholder_ids or "略過語意卡控" in f.message
                             or (f.source == "llm" and f.status == "skipped")))]
        findings += _advisory_from_result(result)
        findings.sort(key=lambda f: (f.category, f.zone, f.check_id, f.target,
                                     f.status, f.message))
        meta["advisory_merged"] = True

        # 代填答案（status: proposed）併入 input/<名>/answers.yaml：
        # 只新增未覆蓋的主題、不動既有條目。待驗證＝不算已答、擋收斂，
        # 使用者把 proposed 改成 answered 才算驗證通過。
        # 答案檔本身壞掉時不改寫（改寫會默默丟掉壞條目），只提醒。
        current_answers = case.answers
        answers_path = answers_mod.locate(ddl_path)
        proposals = _proposals_from_result(result)
        proposed_added = 0
        if proposals and case.answers_problems:
            print(f"  {name}: answers.yaml 有問題，代填答案未寫入"
                  f"（請先修復：{'；'.join(case.answers_problems)}）")
        elif proposals:
            current_answers, proposed_added = answers_mod.add_proposals(
                case.answers, proposals)
            if proposed_added:
                with open(answers_path, "w", encoding="utf-8") as f:
                    f.write(answers_mod.answers_to_yaml(current_answers, name))

        # 迭代收斂帳本：問題母體要以「合併後」的顧問區為準重算
        # （validate 當下顧問區還是待補佔位，算不出真實的待答清單）。
        meta["iteration"] = answers_mod.iteration_summary(
            findings, current_answers, problems=case.answers_problems,
            answers_file=os.path.basename(answers_path))

        # 迭代歷史：合併後（本輪的權威終態）一站式記錄。
        from dataval import iterations as iter_history
        s0 = summarize(findings)
        round_no = iter_history.record_full_round(
            R.ITERATIONS_ROOT, name, ddl_path, meta, findings,
            {"compliant": s0["compliant"], "fails": s0["fail"]})

        outputs = {
            ".report.md": to_markdown(findings, meta),
            ".report.json": to_json(findings, meta),
            ".report.html": to_html(findings, meta),
        }
        R.write_report_outputs(name, round_no, outputs,
                               proposal=meta.get("ddl_proposal"))
        # 每輪報告存檔＋變更報告（合併後為該輪權威終態）
        iter_history.archive_round_outputs(R.ITERATIONS_ROOT, name, round_no,
                                           outputs[".report.md"],
                                           meta["iteration"])
        s = summarize(findings)
        print(f"  {name}: 顧問區已補完（{s['advisory']} 項）→ "
              f"reports/{name}.report.html"
              f"（本輪存檔 {name}.round_{round_no}.report.*）")
        it = meta["iteration"]
        state = "✅ 已收斂" if it["converged"] else "❌ 未收斂"
        print(f"    ↻ 迭代 第 {it['round']}/{it['max_rounds']} 輪："
              f"待答 {it['blockers']['open_questions']}、"
              f"待驗證 {it['blockers']['proposed_unverified']}"
              f"（本次代填 {proposed_added}）、"
              f"已解 {len(it['answered'])}、擱置 {len(it['deferred'])}、"
              f"閘門 fail {it['blockers']['gating_fails']} → {state}"
              + ("" if it["converged"] else
                 f"；驗證：input/{name}/answers.yaml"
                 "（proposed → answered）"))
        if it["round"] >= it["max_rounds"] and not it["converged"]:
            print(f"    ⚠️ 已達迭代上限（{it['max_rounds']} 輪），"
                  "建議收斂範圍或人工決策。")
        merged += 1

    if merged == 0 and guard_failed == 0:
        print("找不到任何 advisory_result.json。請先讓 agent 依 advisory_prompt.md 產生建議。")
    elif merged:
        print(f"完成，合併 {merged} 份。閘門區判定不變。")
    if guard_failed:
        print(f"❌ {guard_failed} 份報告未通過 JSON Schema 或閘門保護，未合併。")
        sys.exit(1)


if __name__ == "__main__":
    main()
