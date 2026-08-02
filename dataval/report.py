"""Report builder: zone-aware JSON + Markdown.

Verdict rule: only GATING-zone findings with status 'fail' and severity 'error'
block. Advisory findings (LLM and design suggestions) are info only.
"""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from .model import Finding, ZONE_GATING, ZONE_ADVISORY

CATEGORY_TITLES = {
    "structural": "結構（欄位／型別／約束）",
    "naming": "命名規則",
    "best_practice": "最佳實踐",
    "ssot": "單一真實源（跨域）",
    "concept": "資料設計概念（主體性）",
    "lineage": "Lineage 關聯治理",
}
_ICON = {"pass": "✅", "warning": "⚠️", "fail": "❌", "info": "ℹ️",
         "skipped": "⏭️"}


def _generated_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def summarize(findings: list[Finding]) -> dict:
    gating = [f for f in findings if f.zone == ZONE_GATING]
    blocking = [f for f in gating if f.status == "fail" and f.severity == "error"]
    by_status = Counter(f.status for f in findings)
    return {
        "total": len(findings),
        "gating": len(gating),
        "advisory": len(findings) - len(gating),
        "pass": by_status.get("pass", 0),
        "warning": by_status.get("warning", 0),
        "fail": by_status.get("fail", 0),
        "info": by_status.get("info", 0),
        "skipped": by_status.get("skipped", 0),
        "compliant": len(blocking) == 0,
        "blocking_count": len(blocking),
    }


def checking_rule_summary(findings: list[Finding],
                          loaded_rule_ids: list[str] | None = None) -> dict:
    """Summarize the design-level outcome directly by checking rule ID.

    A rule is listed once using the strongest gating outcome it produced:
    failed > warning > passed > not_checked. Advisory IDs are kept separate
    because they never participate in the compliance verdict.
    """
    by_rule: dict[str, list[Finding]] = {}
    for f in findings:
        by_rule.setdefault(f.check_id, []).append(f)

    out = {"passed": [], "warnings": [], "failed": [],
           "not_checked": [], "advisory": []}
    for rule_id, items in sorted(by_rule.items()):
        gating = [f for f in items if f.zone == ZONE_GATING]
        advisory = [f for f in items if f.zone == ZONE_ADVISORY]
        if gating:
            if any(f.status == "fail" and f.severity == "error" for f in gating):
                out["failed"].append(rule_id)
            elif any(f.status in ("warning", "fail") for f in gating):
                out["warnings"].append(rule_id)
            elif any(f.status == "pass" for f in gating):
                out["passed"].append(rule_id)
            else:
                out["not_checked"].append(rule_id)
        if advisory:
            out["advisory"].append(rule_id)
    represented = set().union(*(set(ids) for ids in out.values()))
    out["not_checked"].extend(
        rule_id for rule_id in sorted(set(loaded_rule_ids or []))
        if rule_id not in represented)
    return out


# ---- 檢查來源對照：每個 check 對應到 config／input 的哪裡 -----------------
# SKILL.* 規則直接用 compiled bundle 記載的檔案路徑（meta.rule_coverage）；
# 引擎內建檢查用前綴對照。目的：報告內每筆結果都能回溯依據來源。
_BUILTIN_ORIGINS: list[tuple[str, str]] = [
    ("BUSINESS_KEY.METADATA", "input/<名>/context.md（front-matter business_keys）"),
    ("DOMAIN.SCOPE", "input/<名>/context.md（front-matter domains）→ config/<域>/"),
    ("RELATION.CARDINALITY_SAMPLE",
     "input/<名>/relations.yaml 對照 samples/*.csv（基數實檢）"),
    ("LINEAGE.ER_SUGGESTION",
     "config/<域>/erd/*.md（ER 參考模型）對照 relations.yaml"),
    ("LINEAGE.", "input/<名>/relations.yaml（宣告關聯；外部端點對 production/）"),
    ("PRODGRAPH.", "production/<域>/（正式區全域關聯圖）"),
    ("PRODUCTION.", "production/<域>/（已核准 DDL 基準）"),
    ("FLOW.", "config/<域>/flows/*.md（E2E 流程）"),
    ("ERD.TABLE_PURPOSE", "config/<域>/erd/tables/<表名>.md（參考表用途）"),
    ("ERD.ENTITY_REFERENCE",
     "config/<域>/erd/*.md（ER 參考模型 entity 欄位定義）對照本次 DDL"),
    ("PROPOSAL.DDL",
     "config/<域>/erd/*.md（參考模型自動組建；建議值，不影響判定）"),
    ("DERIVATION.",
     "input/<名>/derivation.sql（你的衍生 Join SQL）對照 relations.yaml"
     "／寬表 DDL／建議 SQL"),
    ("SSOT.UNREGISTERED_SUBJECT",
     "config/<域>/ssot/registry.yaml（SSOT 登錄推斷）"),
    ("CONCEPT.SUBJECT", "顧問區 LLM（主體性概念層；情境來自 context.md）"),
    ("NAME.SEMANTIC", "顧問區 LLM（命名語意）"),
    ("SYSTEM.", "輸入／設定檔（訊息內指名壞檔路徑）"),
]


def check_origins(findings: list[Finding], meta: dict) -> dict[str, str]:
    """check_id → 依據來源。SKILL 用規則檔實際路徑；內建檢查用對照表。"""
    origins: dict[str, str] = {}
    for entry in (meta.get("rule_coverage") or {}).get("loaded") or []:
        if entry.get("file"):
            origins[entry["id"]] = f"config/{entry['file']}"
    # naming 字典規則：依據除了規則檔還有詞彙字典本body
    if "SKILL.naming_glossary" in origins:
        origins["SKILL.naming_glossary"] += " ＋ config/<域>/naming/*.md（詞彙字典）"
    for f in findings:
        if f.check_id in origins:
            continue
        for prefix, text in _BUILTIN_ORIGINS:
            if f.check_id == prefix or f.check_id.startswith(prefix):
                origins[f.check_id] = text
                break
        else:
            origins[f.check_id] = "引擎內建檢查（dataval/）"
    return origins


# 涵蓋清單用的結果標籤：把 checking rule ID 摘要反轉成「每條規則 → 結果」。
_COVERAGE_OUTCOME = {
    "failed": ("❌ 擋下", "bs-fail"),
    "warnings": ("⚠️ 警告", "bs-warn"),
    "passed": ("✅ 通過", "bs-pass"),
    "not_checked": ("ℹ️ 未實檢／略過", "bs-info"),
    "advisory": ("💡 顧問", "bs-advisory"),
}


def _rule_outcome_map(findings: list[Finding], meta: dict) -> dict:
    """rule_id → 結果分類鍵。閘門結果優先於顧問，供涵蓋清單逐條標註。"""
    crs = checking_rule_summary(findings, meta.get("checking_rule_ids_loaded"))
    out: dict[str, str] = {}
    for key in ("failed", "warnings", "passed", "not_checked", "advisory"):
        for rule_id in crs[key]:
            out.setdefault(rule_id, key)
    return out


def rule_coverage_lines(meta: dict, findings: list[Finding]) -> list[str]:
    """規則涵蓋清單（Markdown）：交代 config 每一條規則本次的去向。

    純透明度區塊——不影響合規判定。回答「宣告的域底下每條規則是否都執行、
    被略過的是哪些、為什麼」。"""
    cov = meta.get("rule_coverage") or {}
    if not cov:
        return []
    outcomes = _rule_outcome_map(findings, meta)
    requested = cov.get("requested_domains") or []
    available = cov.get("available_domains") or []
    loaded = cov.get("loaded") or []
    not_loaded = cov.get("not_loaded") or []
    empty_domains = cov.get("empty_domains") or []
    lines = ["## 規則涵蓋清單"]
    lines.append(
        f"> 宣告域（context.md）：{('、'.join(requested)) or '（未指定，僅 Common）'}"
        f" · config 可用域：{('、'.join(available)) or '—'}")
    lines.append(
        f"> 涵蓋：載入並執行 **{cov.get('rules_loaded_count', 0)}** 條 "
        f"／ config 共 **{cov.get('rules_total', 0)}** 條")
    lines.append("")

    lines.append(f"### ✅ 已載入並執行（{len(loaded)} 條）")
    if loaded:
        for r in loaded:
            label = _COVERAGE_OUTCOME.get(outcomes.get(r["id"], "not_checked"),
                                          _COVERAGE_OUTCOME["not_checked"])[0]
            src = f" ｜ config/{r['file']}" if r.get("file") else ""
            lines.append(f"- `{r['id']}`（{r['domain']}）→ {label}{src}")
    else:
        lines.append("（無）")
    lines.append("")

    lines.append(f"### ⏭️ 未載入：所屬域未在 context.md 宣告（{len(not_loaded)} 條）")
    if not_loaded:
        by_domain: dict[str, list[str]] = {}
        for r in not_loaded:
            by_domain.setdefault(r["domain"], []).append(r["id"])
        for dom in sorted(by_domain):
            ids = "、".join(f"`{x}`" for x in by_domain[dom])
            lines.append(f"- **{dom}**：{ids}")
        lines.append("> 若這些域也應納入檢查，請在 context.md front-matter 的 "
                     "`domains` 補上該域後重跑。")
    else:
        lines.append("（無——宣告域底下的規則已全數載入）")
    lines.append("")

    if empty_domains:
        lines.append("### ⚠️ 空的域（資料夾存在但無任何規則）")
        lines.append("- " + "、".join(empty_domains))
        lines.append("")
    return lines


def iteration_lines(meta: dict) -> list[str]:
    """迭代收斂區塊（Markdown）：問答迴圈的第幾輪、待答／已解／擱置與收斂判定。"""
    it = meta.get("iteration") or {}
    if not it:
        return []
    lines = [f"## 迭代收斂（第 {it.get('round', 1)} 輪／上限 {it.get('max_rounds', 5)}）"]
    lines.append("> 收斂條件：無待答問題 ＋ 閘門合規")
    blockers = it.get("blockers") or {}
    if it.get("converged"):
        lines.append("> 目前：✅ **已收斂**")
    elif it.get("advisory_pending"):
        lines.append("> 目前：⏳ 顧問區尚未補完——待答題數要等補完後才能確定"
                     f"（閘門 fail {blockers.get('gating_fails', 0)} 項）")
    else:
        lines.append(f"> 目前：❌ 未收斂 —— 待答 {blockers.get('open_questions', 0)} 題、"
                     f"待驗證 {blockers.get('proposed_unverified', 0)} 題、"
                     f"閘門 fail {blockers.get('gating_fails', 0)} 項")
    if it.get("round", 1) >= it.get("max_rounds", 5) and not it.get("converged"):
        lines.append("> ⚠️ **已達迭代上限**——建議收斂問題範圍或人工決策。")
    for problem in it.get("answers_problems") or []:
        lines.append(f"> ⚠️ 答案檔問題：{problem}")
    lines.append("")

    open_topics = it.get("open") or []
    if not it.get("advisory_pending"):
        lines.append(f"### ❓ 待答（{len(open_topics)}）")
        if open_topics:
            for topic in open_topics:
                lines.append(f"- `{topic['id']}` {topic['question']}")
        else:
            lines.append("（無）")
        lines.append("")

    proposed = it.get("proposed") or []
    if proposed:
        lines.append(f"### 🟡 待驗證：agent 代填，請確認（{len(proposed)}）")
        for e in proposed:
            tag = e.get("kind", "semantic")
            if e.get("applied_to"):
                tag += f" → 建議改 {e['applied_to']}"
            lines.append(f"- `{e['id']}`（{tag}）")
            if e.get("question"):
                lines.append(f"  - Q: {e['question']}")
            lines.append(f"  - 代填答案: {e.get('answer', '')}")
        lines.append("> 驗證：到 input/<名>/answers.yaml 把 `status: proposed` 改為 "
                     "`answered`（答案可修改；不想追的改 `deferred`）。"
                     "待驗證不算已答，會擋收斂。")
        lines.append("")

    answered = it.get("answered") or []
    lines.append(f"### ✅ 已解（{len(answered)}）")
    if answered:
        for e in answered:
            tag = e.get("kind", "semantic")
            if e.get("applied_to"):
                tag += f" → 已改 {e['applied_to']}"
            snippet = (e.get("answer") or "").replace("\n", " ")[:80]
            lines.append(f"- `{e['id']}`（{tag}）{snippet}")
    else:
        lines.append("（無）")
    lines.append("")

    deferred = it.get("deferred") or []
    if deferred:
        lines.append(f"### ⏸ 擱置（{len(deferred)}）")
        for e in deferred:
            reason = (e.get("answer") or "").replace("\n", " ")[:80]
            lines.append(f"- `{e['id']}`" + (f"（{reason}）" if reason else ""))
        lines.append("")

    # 本輪 input 相對前一輪改了什麼（iterations/<名>/ 快照比對）
    changes = it.get("input_changes")
    if changes is not None:
        lines.append("### 📝 本輪 input 變更")
        if changes.get("baseline_round") is None:
            lines.append("（首輪——無前輪可比；本輪輸入已快照到 iterations/）")
        else:
            lines.append(f"（vs 第 {changes['baseline_round']} 輪）")
            for f in changes.get("files") or []:
                if f["status"] == "changed":
                    lines.append(f"- `{f['file']}`：變更（+{f.get('added', 0)}"
                                 f"／−{f.get('removed', 0)} 行）")
                elif f["status"] == "added":
                    lines.append(f"- `{f['file']}`：新增")
                elif f["status"] == "removed":
                    lines.append(f"- `{f['file']}`：移除")
                else:
                    lines.append(f"- `{f['file']}`：不變")
        lines.append("")

    # 與前一輪相比的發現變化（明細在 iterations/<名>/round_N.delta.md）
    delta = it.get("findings_delta")
    if delta and delta.get("baseline_round") is not None:
        lines.append(f"### 🔄 與第 {delta['baseline_round']} 輪相比的發現變化")
        lines.append(f"- 新增 {len(delta.get('new') or [])}、"
                     f"解決 {len(delta.get('resolved') or [])}、"
                     f"狀態變化 {len(delta.get('changed') or [])}"
                     f"（明細：iterations/<名>/round_{it.get('round', 1)}.delta.md；"
                     f"該輪完整報告：round_{it.get('round', 1)}.report.md）")
        lines.append("")

    # 收斂（最後一輪）：初版 ↔ 終版 input 差異
    first_last = it.get("first_last")
    if first_last:
        lines.append(f"### 🏁 初版（第 {first_last['first_round']} 輪）↔ "
                     f"終版（第 {first_last['last_round']} 輪）input 差異")
        for f in first_last.get("files") or []:
            if f["status"] == "unchanged":
                lines.append(f"- `{f['file']}`：不變")
                continue
            lines.append(f"- `{f['file']}`：{f['status']}"
                         f"（+{f.get('added', 0)}／−{f.get('removed', 0)} 行）"
                         + ("（diff 過長已截斷，全文見 iterations/）"
                            if f.get("truncated") else ""))
            if f.get("diff"):
                lines.append("```diff")
                lines.append(f["diff"])
                lines.append("```")
        lines.append("")
    return lines


def proposal_lines(meta: dict) -> list[str]:
    """建議 DDL 對比區塊（Markdown）：Join SQL＋未來 DDL＋與 input 逐欄對比。"""
    p = meta.get("ddl_proposal")
    if not p:
        return []
    lines = ["## 建議 DDL 對比（依參考模型自動組建；建議值，不影響判定）"]
    lines.append(f"> 基底表 `{p['base_table']}` · 涵蓋 entity："
                 + "、".join(f"`{e}`" for e in p["entities"])
                 + f" · 依據：{('、'.join(p['sources'])) or 'config/<域>/erd'}")
    if p.get("not_in_input"):
        lines.append("> ⚠️ 參考模型有、但 input 尚未涵蓋的表："
                     + "、".join(f"`{t}`" for t in p["not_in_input"]))
    for warning in p.get("warnings") or []:
        lines.append(f"> ⚠️ {warning}")
    evolution = p.get("evolution")
    if evolution:
        if evolution.get("baseline_round") is None:
            lines.append("> 🧬 本輪為**首次產生**的建議。")
        elif not evolution.get("changed"):
            lines.append(f"> 🧬 與第 {evolution['baseline_round']} 輪建議相比：**不變**。")
        else:
            lines.append(f"> 🧬 與第 {evolution['baseline_round']} 輪建議相比：**已演進**"
                         "（diff 見下）。")
    lines.append("")
    if evolution and evolution.get("changed") and evolution.get("sql_diff") is not None:
        lines.append(f"### 🧬 建議演進（vs 第 {evolution['baseline_round']} 輪）")
        for key, title in (("sql_diff", "Join SQL"), ("ddl_diff", "未來 DDL")):
            if evolution.get(key):
                lines.append(f"**{title}**")
                lines.append("```diff")
                lines.append(evolution[key])
                lines.append("```")
        if evolution.get("truncated"):
            lines.append("（diff 過長已截斷，全文見 iterations/<名>/round_N.proposal.md）")
        lines.append("")
    lines.append("### 建議 Join SQL")
    lines.append("```sql")
    lines.append(p["join_sql"])
    lines.append("```")
    lines.append("")
    lines.append(f"### 未來 DDL（建議：`{p['table_name']}`）")
    lines.append("```sql")
    lines.append(p["proposed_ddl"])
    lines.append("```")
    lines.append("")
    lines.append("### 與 input DDL 的逐欄對比")
    lines.append("| 建議欄位 | 型別 | 來源 entity | input 落點 |")
    lines.append("|---|---|---|---|")
    for c in p.get("comparison") or []:
        located = "、".join(f"`{t}`" for t in c["in_input"]) or "❌ input 未包含"
        lines.append(f"| `{c['column']}` | {c['type']} | `{c['from_entity']}` "
                     f"| {located} |")
    input_only = p.get("input_only") or []
    if input_only:
        lines.append("")
        lines.append(f"**input 獨有欄位（建議模型未涵蓋，{len(input_only)}）**：")
        lines.append("、".join(f"`{c['table']}.{c['column']}`"
                               for c in input_only))
    lines.append("")
    return lines


def derivation_lines(meta: dict) -> list[str]:
    """衍生 SQL 對照區塊（Markdown）：你的 Join SQL＋三方鍵矩陣＋欄位覆蓋。"""
    d = meta.get("derivation")
    if not d:
        return []
    lines = [f"## 衍生 SQL 對照（input/<名>/{d['file']}）"]
    lines.append(f"> 基底表 `{d['base_table']}` · 來源表 "
                 + "、".join(f"`{t}`" for t in d["source_tables"])
                 + f" · join {d['join_count']} 組 · 輸出欄 {d['output_count']}"
                 + (f"（表達式 {d['expression_count']}）"
                    if d["expression_count"] else ""))
    cov = d.get("coverage")
    if cov:
        lines.append(f"> 對應寬表 `{cov['wide_table']}`：欄位覆蓋 "
                     f"{cov['covered']}/{cov['ddl_columns']}"
                     + (f"；DDL 有但 SQL 沒產出：{cov['missing_in_sql']}"
                        if cov["missing_in_sql"] else "")
                     + (f"；SQL 產出但 DDL 沒有：{cov['extra_in_sql']}"
                        if cov["extra_in_sql"] else "")
                     + ("；含 SELECT *（無法逐欄對照）"
                        if cov.get("has_star") else ""))
    lines.append("")
    lines.append("### 你的 Join SQL")
    lines.append("```sql")
    lines.append(d["sql"])
    lines.append("```")
    lines.append("")
    matrix = d.get("key_matrix") or []
    if matrix:
        header = "| join 鍵 | 你的 SQL | relations.yaml |"
        divider = "|---|---|---|"
        if d.get("has_proposal"):
            header += " 建議 SQL |"
            divider += "---|"
        lines.append("### join 鍵三方對照")
        lines.append(header)
        lines.append(divider)
        for row in matrix:
            cells = [f"`{row['pair']}`",
                     "✅" if row["in_sql"] else "❌",
                     "✅" if row["in_relations"] else "❌"]
            if d.get("has_proposal"):
                cells.append("✅" if row["in_proposal"] else "❌")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return lines


def blocking_summary(findings: list[Finding]) -> dict:
    """依「規則」彙整本次卡控結果：哪些規則把設計卡下來、擋了哪些對象。

    回傳 {"blocked": [...], "warned": [...]}，每項含 rule（check_id）、
    title（從訊息取的規則名）、targets（被擋對象）、reason（違規描述示例）。"""
    def _agg(items):
        by_rule: dict[str, dict] = {}
        for f in items:
            title = f.message.split("：", 1)[0] if "：" in f.message else f.check_id
            reason = f.message.split("：", 1)[1] if "：" in f.message else f.message
            e = by_rule.setdefault(f.check_id, {"rule": f.check_id, "title": title,
                                                "targets": [], "reason": reason})
            if f.target not in e["targets"]:
                e["targets"].append(f.target)
        return sorted(by_rule.values(), key=lambda x: x["rule"])
    gating = [f for f in findings if f.zone == ZONE_GATING]
    return {
        "blocked": _agg([f for f in gating if f.status == "fail" and f.severity == "error"]),
        "warned": _agg([f for f in gating if f.status == "warning"]),
    }


def to_json(findings: list[Finding], meta: dict | None = None,
            deterministic: bool = False) -> str:
    gating = [f.to_dict() for f in findings if f.zone == ZONE_GATING]
    advisory = [f.to_dict() for f in findings if f.zone == ZONE_ADVISORY]
    meta = meta or {}
    payload = {
        "meta": meta,
        "summary": summarize(findings),
        "checking_rule_summary": checking_rule_summary(
            findings, meta.get("checking_rule_ids_loaded")),
        "check_origins": check_origins(findings, meta),
        "rule_coverage": meta.get("rule_coverage", {}),
        "ddl_proposal": meta.get("ddl_proposal") or {},
        "derivation": meta.get("derivation") or {},
        "iteration": meta.get("iteration", {}),
        "blocking_summary": blocking_summary(findings),
        "lineage": meta.get("lineage", {}),
        # Two zones kept as separate sections so the deterministic gating result
        # is clearly distinguished from advisory/LLM output. The flat "findings"
        # list is retained for backward compatibility.
        "gating_zone": {
            "note": "確定性檢查，決定合規判定；結果以 checking rule ID 呈現",
            "findings": gating,
        },
        "advisory_zone": {
            "note": "LLM／語意建議，一律 info，永不影響合規判定，不保證可重複",
            "findings": advisory,
        },
        "findings": [f.to_dict() for f in findings],
    }
    # Timestamp is excluded in deterministic mode so the same input yields a
    # byte-identical file (useful for diffing / verifying the gating result).
    if not deterministic:
        payload["generated_at"] = _generated_at()
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def to_markdown(findings: list[Finding], meta: dict | None = None) -> str:
    s = summarize(findings)
    verdict = "✅ 合規" if s["compliant"] else "❌ 不合規"
    meta = meta or {}
    round_no = (meta.get("iteration") or {}).get("round")
    max_rounds = (meta.get("iteration") or {}).get("max_rounds", 5)
    title = ("# 資料設計驗證報告" if not round_no
             else f"# 資料設計驗證報告 — 第 {round_no} 輪迭代")
    lines = [
        title,
        f"_產生時間 {_generated_at()}_<br>",
    ] + ([f"**🔁 第 {round_no}／{max_rounds} 輪迭代報告**<br>"]
         if round_no else []) + [
        f"**判定：{verdict}**（會擋項目 {s['blocking_count']}）<br>",
        f"通過 {s['pass']} · 警告 {s['warning']} · 失敗 {s['fail']} · "
        f"略過 {s['skipped']} · 提示 {s['info']}<br>",
        f"閘門區 {s['gating']} 項 · 顧問區 {s['advisory']} 項<br>",
    ]
    if meta:
        lines.append(f"> 方言 {meta.get('dialect')} · 表數 {meta.get('tables')} "
                     f"· 載入 skill {meta.get('skills_loaded', 0)} 條")
        bundle = (meta.get("validation_manifest") or {}).get(
            "validation_bundle_code")
        if bundle:
            lines.append(f"> 驗證 bundle `{bundle}`（含規則、validator 與依賴版本）")
    lines.append("")

    # checking rule ID 總覽：不用指紋，直接呈現各規則的設計級結果。
    crs = checking_rule_summary(findings, meta.get("checking_rule_ids_loaded"))
    lines.append("## Checking rule ID 摘要")
    labels = (("failed", "❌ 擋下"), ("warnings", "⚠️ 警告"),
              ("passed", "✅ 通過"), ("not_checked", "ℹ️ 未實檢／略過"),
              ("advisory", "💡 顧問"))
    for key, label in labels:
        ids = crs[key]
        lines.append(f"- {label}：" + ("、".join(f"`{x}`" for x in ids) if ids else "（無）"))
    lines.append("")

    lines.extend(rule_coverage_lines(meta, findings))
    lines.extend(iteration_lines(meta))
    lines.extend(proposal_lines(meta))
    lines.extend(derivation_lines(meta))

    lineage = meta.get("lineage") or {}
    relationships = lineage.get("relationships") or []
    lines.append("## Lineage 關聯")
    lines.append(f"> {lineage.get('note') or '本次沒有 lineage 資訊。'}")
    lines.append("")
    if relationships:
        lines.append("| 來源 | 目標 | 欄位映射 | 性質 |")
        lines.append("|---|---|---|---|")
        kind_labels = {
            "declared": "YAML 明確宣告",
            "suggested": "系統建議（方向待確認）",
            "suggested-undirected": "系統建議（方向未知）",
            "er-suggested": "ER diagram 建議（方向待確認）",
            "er-undirected": "ER diagram 關聯（方向未知）",
        }
        for relation in relationships:
            mappings = "<br>".join(
                f"`{item.get('source', '')}` → `{item.get('target', '')}`"
                for item in relation.get("columns", []))
            if not mappings:
                mappings = (f"ER 關係：`{relation['label']}`"
                            if relation.get("label") else "（未宣告欄位映射）")
            source = str(relation.get("source", "")).replace("|", "\\|")
            target = str(relation.get("target", "")).replace("|", "\\|")
            kind = ("YAML 宣告＋ER 對應" if relation.get("er_confirmed") else
                    kind_labels.get(relation.get("kind"),
                                    str(relation.get("kind", ""))))
            lines.append(f"| `{source}` | `{target}` | {mappings} | {kind} |")
    else:
        lines.append("（無關聯）")
    lines.append("")

    # 本次卡控摘要 — 依規則描述：這次是被哪幾條規則卡下來的
    bs = blocking_summary(findings)
    if bs["blocked"] or bs["warned"]:
        lines.append("## 本次卡控摘要（被哪些規則卡下來）")
        if bs["blocked"]:
            lines.append("**擋下（不合規的原因）：**")
            for b in bs["blocked"]:
                lines.append(f"- `{b['rule']}` {b['title']} → 擋下 "
                             f"{'、'.join(b['targets'])}（{b['reason'][:60]}）")
        if bs["warned"]:
            lines.append("")
            lines.append("**警告（放行但需注意）：**")
            for b in bs["warned"]:
                lines.append(f"- `{b['rule']}` {b['title']} → "
                             f"{'、'.join(b['targets'])}")
        lines.append("")

    origins = check_origins(findings, meta)
    for cat, title in CATEGORY_TITLES.items():
        cat_f = [f for f in findings if f.category == cat]
        if not cat_f:
            continue
        lines.append(f"## {title}")
        cat_f.sort(key=lambda f: (f.status != "fail", f.status != "warning",
                                  f.status != "skipped", f.status != "info"))
        lines.append("")
        lines.append("| | 區 | 檢查 | 對象 | 說明 | 來源 |")
        lines.append("|---|---|---|---|---|---|")
        for f in cat_f:
            zone = "閘門" if f.zone == ZONE_GATING else "顧問"
            msg = f.message.replace("|", "\\|")
            if f.expected or f.actual:
                msg += (f" <br>**期望** {f.expected} ｜ **實際** {f.actual}"
                        ).replace("|", "\\|").replace("\\|｜\\|", "｜")
            if f.fix:
                msg += f" <br>**修法** {f.fix}".replace("|", "\\|")
            if f.rationale:
                msg += f" <br>_理由：{f.rationale}_".replace("|", "\\|")
            if origins.get(f.check_id):
                msg += (f" <br>_依據：{origins[f.check_id]}_"
                        ).replace("|", "\\|")
            lines.append(f"| {_ICON.get(f.status,'')} | {zone} | `{f.check_id}` | "
                         f"`{f.target}` | {msg} | {f.source} |")
        lines.append("")
    return "\n".join(lines)


# ---- HTML report (single self-contained file, lightweight interactivity) ----
import html as _html


def _esc(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _card(head: str, body: str, collapsed: bool = False) -> str:
    """摺疊式摘要卡片：點標題列展開／收合（減少長報告的捲動量）。"""
    cls = "bsum collapsed" if collapsed else "bsum"
    return (f'<div class="{cls}"><div class="bs-head" onclick="toggleCard(this)">'
            f'<span class="chev">▾</span>{head}</div>'
            f'<div class="bs-body">{body}</div></div>')


def _lineage_html(meta: dict) -> str:
    lineage = meta.get("lineage") or {}
    relationships = lineage.get("relationships") or []
    note = _esc(lineage.get("note") or "本次沒有 lineage 資訊。")
    if not relationships:
        body = '<div class="bs-row"><span class="bs-t">（無關聯）</span></div>'
    else:
        kind_labels = {
            "declared": "YAML 明確宣告",
            "suggested": "系統建議（方向待確認）",
            "suggested-undirected": "系統建議（方向未知）",
            "er-suggested": "ER diagram 建議（方向待確認）",
            "er-undirected": "ER diagram 關聯（方向未知）",
        }
        rows = []
        for relation in relationships:
            mappings = "、".join(
                f"{_esc(item.get('source'))} → {_esc(item.get('target'))}"
                for item in relation.get("columns", []))
            if not mappings:
                mappings = (f"ER 關係：{_esc(relation['label'])}"
                            if relation.get("label") else "未宣告欄位映射")
            kind = ("YAML 宣告＋ER 對應" if relation.get("er_confirmed") else
                    kind_labels.get(relation.get("kind"), relation.get("kind", "")))
            arrow = "↔" if relation.get("kind") in (
                "suggested-undirected", "er-undirected") else "→"
            rows.append(
                '<div class="bs-row">'
                f'<span class="mono bs-title">{_esc(relation.get("source"))}</span>'
                f'<span class="bs-t">{arrow}</span>'
                f'<span class="mono bs-title">{_esc(relation.get("target"))}</span>'
                f'<span class="bs-t">欄位：{mappings}</span>'
                f'<span class="badge zone-{("gating" if relation.get("kind") == "declared" else "advisory")}">'
                f'{_esc(kind)}</span></div>')
        body = "".join(rows)
    return _card(f'Lineage 關聯<span class="bs-hint">{note}</span>', body,
                 collapsed=True)


def _blocking_summary_html(findings: list[Finding]) -> str:
    """卡控摘要卡片：本次被哪些規則卡下來（點規則可篩選明細）。"""
    bs = blocking_summary(findings)
    if not bs["blocked"] and not bs["warned"]:
        return ""
    rows = []
    for b in bs["blocked"]:
        rows.append(
            f'<div class="bs-row"><span class="bs-dot bs-fail"></span>'
            f'<a href="#" onclick="filterRule(\'{_esc(b["rule"])}\');return false" '
            f'class="mono bs-rule">{_esc(b["rule"])}</a>'
            f'<span class="bs-title">{_esc(b["title"])}</span>'
            f'<span class="bs-t">擋下：{_esc("、".join(b["targets"]))}</span></div>')
    for b in bs["warned"]:
        rows.append(
            f'<div class="bs-row"><span class="bs-dot bs-warn"></span>'
            f'<a href="#" onclick="filterRule(\'{_esc(b["rule"])}\');return false" '
            f'class="mono bs-rule">{_esc(b["rule"])}</a>'
            f'<span class="bs-title">{_esc(b["title"])}</span>'
            f'<span class="bs-t">警告：{_esc("、".join(b["targets"]))}</span></div>')
    return _card('本次卡控摘要 — 被哪些規則卡下來'
                 '<span class="bs-hint">（點規則代號可篩選明細）</span>',
                 "".join(rows))


def _checking_rule_summary_html(findings: list[Finding], meta: dict) -> str:
    crs = checking_rule_summary(findings, meta.get("checking_rule_ids_loaded"))
    rows = []
    for key, label, css in (
            ("failed", "擋下", "bs-fail"),
            ("warnings", "警告", "bs-warn"),
            ("passed", "通過", "bs-pass"),
            ("not_checked", "未實檢／略過", "bs-info"),
            ("advisory", "顧問", "bs-advisory")):
        ids = crs[key]
        if not ids:
            continue
        links = "、".join(
            f'<a href="#" onclick="filterRule(\'{_esc(rule_id)}\');return false" '
            f'class="mono bs-rule">{_esc(rule_id)}</a>' for rule_id in ids)
        rows.append(f'<div class="bs-row"><span class="bs-dot {css}"></span>'
                    f'<span class="bs-title">{label}</span><span class="bs-t">{links}</span></div>')
    return _card('Checking rule ID 摘要'
                 '<span class="bs-hint">（點 rule ID 可篩選明細）</span>',
                 "".join(rows))


def _rule_coverage_html(meta: dict, findings: list[Finding]) -> str:
    """規則涵蓋清單卡片：交代 config 每條規則本次的去向（純透明度，不影響判定）。"""
    cov = meta.get("rule_coverage") or {}
    if not cov:
        return ""
    outcomes = _rule_outcome_map(findings, meta)
    requested = cov.get("requested_domains") or []
    available = cov.get("available_domains") or []
    loaded = cov.get("loaded") or []
    not_loaded = cov.get("not_loaded") or []
    empty_domains = cov.get("empty_domains") or []

    rows = [
        '<div class="bs-row"><span class="bs-t">宣告域（context.md）：'
        f'{_esc("、".join(requested) or "（未指定，僅 Common）")} · config 可用域：'
        f'{_esc("、".join(available) or "—")}</span></div>',
        '<div class="bs-row"><span class="bs-title">已載入並執行 '
        f'{_esc(cov.get("rules_loaded_count", 0))} 條</span>'
        f'<span class="bs-t">／ config 共 {_esc(cov.get("rules_total", 0))} 條</span></div>',
    ]
    for r in loaded:
        label, css = _COVERAGE_OUTCOME.get(
            outcomes.get(r["id"], "not_checked"), _COVERAGE_OUTCOME["not_checked"])
        src = (f'<span class="bs-t mono">config/{_esc(r["file"])}</span>'
               if r.get("file") else "")
        rows.append(
            f'<div class="bs-row"><span class="bs-dot {css}"></span>'
            f'<a href="#" onclick="filterRule(\'{_esc(r["id"])}\');return false" '
            f'class="mono bs-rule">{_esc(r["id"])}</a>'
            f'<span class="bs-t">{_esc(r["domain"])}</span>'
            f'<span class="bs-t">{_esc(label)}</span>{src}</div>')

    if not_loaded:
        by_domain: dict[str, list[str]] = {}
        for r in not_loaded:
            by_domain.setdefault(r["domain"], []).append(r["id"])
        detail = "；".join(
            f"{_esc(dom)}：" + "、".join(_esc(x) for x in by_domain[dom])
            for dom in sorted(by_domain))
        rows.append(
            '<div class="bs-row"><span class="bs-dot bs-info"></span>'
            f'<span class="bs-title">未載入（域未宣告）{len(not_loaded)} 條</span>'
            f'<span class="bs-t">{detail} — 若應納入，請在 context.md 的 domains 補上</span></div>')
    if empty_domains:
        rows.append(
            '<div class="bs-row"><span class="bs-dot bs-warn"></span>'
            '<span class="bs-title">空的域（無任何規則）</span>'
            f'<span class="bs-t">{_esc("、".join(empty_domains))}</span></div>')

    return _card('規則涵蓋清單<span class="bs-hint">（config 每條規則的去向；'
                 '純透明度，不影響判定）</span>',
                 "".join(rows), collapsed=True)


def _iteration_html(meta: dict) -> str:
    """迭代收斂卡片：問答迴圈狀態（進度、待答／已解／擱置、收斂判定）。"""
    it = meta.get("iteration") or {}
    if not it:
        return ""
    blockers = it.get("blockers") or {}
    open_topics = it.get("open") or []
    proposed = it.get("proposed") or []
    answered = it.get("answered") or []
    deferred = it.get("deferred") or []
    round_no, max_rounds = it.get("round", 1), it.get("max_rounds", 5)

    if it.get("converged"):
        state = '<span class="badge" style="background:var(--ok-bg);color:var(--ok)">✅ 已收斂</span>'
    elif it.get("advisory_pending"):
        state = ('<span class="badge" style="background:var(--warn-bg);color:var(--warn)">'
                 '⏳ 顧問區待補完</span>')
    else:
        state = ('<span class="badge" style="background:var(--bad-bg);color:var(--bad)">'
                 f'❌ 未收斂：待答 {blockers.get("open_questions", 0)}、'
                 f'待驗證 {blockers.get("proposed_unverified", 0)}、'
                 f'閘門 fail {blockers.get("gating_fails", 0)}</span>')

    total = len(open_topics) + len(proposed) + len(answered)
    progress = ""
    if total and not it.get("advisory_pending"):
        pct = int(len(answered) * 100 / total)
        progress = (f'<div class="bs-row"><span class="bs-t">收斂進度 '
                    f'已解 {len(answered)}/{total} · 待驗證 {len(proposed)}'
                    f' · 擱置 {len(deferred)}</span>'
                    f'<span style="flex:1;min-width:120px;height:8px;border-radius:4px;'
                    f'background:var(--line);overflow:hidden">'
                    f'<span style="display:block;width:{pct}%;height:100%;'
                    f'background:var(--ok)"></span></span></div>')

    rows = [progress] if progress else []
    if round_no >= max_rounds and not it.get("converged"):
        rows.append('<div class="bs-row"><span class="bs-dot bs-fail"></span>'
                    '<span class="bs-title" style="color:var(--bad)">已達迭代上限——'
                    '建議收斂問題範圍或人工決策</span></div>')
    for problem in it.get("answers_problems") or []:
        rows.append('<div class="bs-row"><span class="bs-dot bs-warn"></span>'
                    f'<span class="bs-t">答案檔問題：{_esc(problem)}</span></div>')
    for topic in open_topics:
        rows.append('<div class="bs-row"><span class="bs-dot bs-warn"></span>'
                    f'<span class="mono bs-rule">{_esc(topic["id"])}</span>'
                    f'<span class="bs-t">❓ {_esc(topic["question"])}</span></div>')
    for e in proposed:
        tag = e.get("kind", "semantic")
        if e.get("applied_to"):
            tag += f" → 建議改 {e['applied_to']}"
        rows.append('<div class="bs-row"><span class="bs-dot bs-advisory"></span>'
                    f'<span class="mono bs-rule">{_esc(e["id"])}</span>'
                    f'<span class="bs-t">🟡 待驗證（{_esc(tag)}）代填答案：'
                    f'{_esc(e.get("answer") or "")}</span></div>')
    for e in answered:
        tag = e.get("kind", "semantic")
        if e.get("applied_to"):
            tag += f" → 已改 {e['applied_to']}"
        rows.append('<div class="bs-row"><span class="bs-dot bs-pass"></span>'
                    f'<span class="mono bs-rule">{_esc(e["id"])}</span>'
                    f'<span class="bs-t">✅（{_esc(tag)}）'
                    f'{_esc((e.get("answer") or "")[:80])}</span></div>')
    for e in deferred:
        rows.append('<div class="bs-row"><span class="bs-dot bs-info"></span>'
                    f'<span class="mono bs-rule">{_esc(e["id"])}</span>'
                    f'<span class="bs-t">⏸ 擱置'
                    f'{_esc((e.get("answer") or "")[:60])}</span></div>')
    if it.get("advisory_pending"):
        rows.append('<div class="bs-row"><span class="bs-dot bs-info"></span>'
                    '<span class="bs-t">待答清單要等顧問區補完後（merge_advisory）'
                    '才能確定。</span></div>')

    changes = it.get("input_changes")
    if changes is not None:
        if changes.get("baseline_round") is None:
            rows.append('<div class="bs-row"><span class="bs-dot bs-info"></span>'
                        '<span class="bs-t">📝 首輪——input 已快照到 iterations/，'
                        '無前輪可比</span></div>')
        else:
            parts = []
            for f in changes.get("files") or []:
                if f["status"] == "changed":
                    parts.append(f"{f['file']}（+{f.get('added', 0)}"
                                 f"／−{f.get('removed', 0)}）")
                elif f["status"] in ("added", "removed"):
                    parts.append(f"{f['file']}（{f['status']}）")
            rows.append('<div class="bs-row"><span class="bs-dot bs-info"></span>'
                        f'<span class="bs-t">📝 本輪 input 變更'
                        f'（vs 第 {changes["baseline_round"]} 輪）：'
                        f'{_esc("、".join(parts)) or "（無）"}</span></div>')

    delta = it.get("findings_delta")
    if delta and delta.get("baseline_round") is not None:
        rows.append('<div class="bs-row"><span class="bs-dot bs-info"></span>'
                    f'<span class="bs-t">🔄 與第 {delta["baseline_round"]} 輪相比：'
                    f'新增 {len(delta.get("new") or [])}、'
                    f'解決 {len(delta.get("resolved") or [])}、'
                    f'狀態變化 {len(delta.get("changed") or [])}'
                    f'（明細：iterations/&lt;名&gt;/round_'
                    f'{it.get("round", 1)}.delta.md）</span></div>')

    first_last = it.get("first_last")
    if first_last:
        diff_blocks = []
        for f in first_last.get("files") or []:
            if f["status"] == "unchanged" or not f.get("diff"):
                continue
            note = ("（diff 過長已截斷，全文見 iterations/）"
                    if f.get("truncated") else "")
            diff_blocks.append(
                f'<details><summary class="mono">{_esc(f["file"])} '
                f'（+{f.get("added", 0)}／−{f.get("removed", 0)} 行）{note}'
                f'</summary><pre class="diff">{_esc(f["diff"])}</pre></details>')
        rows.append('<div class="bs-row"><span class="bs-dot bs-pass"></span>'
                    f'<span class="bs-title">🏁 初版（第 {first_last["first_round"]} 輪）'
                    f'↔ 終版（第 {first_last["last_round"]} 輪）input 差異</span>'
                    '<span class="bs-t">點檔名展開 diff</span></div>'
                    + "".join(diff_blocks))

    hint = ("收斂條件：無待答＋無待驗證＋閘門合規；驗證：input/<名>/answers.yaml "
            "把 proposed 改成 answered")
    return _card(f'迭代收斂 — 第 {round_no}/{max_rounds} 輪 {state}'
                 f'<span class="bs-hint">{hint}</span>',
                 "".join(rows))


def _proposal_html(meta: dict) -> str:
    """建議 DDL 對比卡片：Join SQL／未來 DDL（details 摺疊）＋逐欄對比表。"""
    p = meta.get("ddl_proposal")
    if not p:
        return ""
    rows = [
        '<div class="bs-row"><span class="bs-t">基底表 '
        f'<span class="mono">{_esc(p["base_table"])}</span> · 涵蓋 entity：'
        f'{_esc("、".join(p["entities"]))} · 依據：'
        f'<span class="mono">{_esc("、".join(p.get("sources") or []) or "config/<域>/erd")}'
        '</span></div>'.replace("</span></div>", "</span></span></div>"),
    ]
    if p.get("not_in_input"):
        rows.append('<div class="bs-row"><span class="bs-dot bs-warn"></span>'
                    '<span class="bs-t">⚠️ 參考模型有、input 尚未涵蓋的表：'
                    f'{_esc("、".join(p["not_in_input"]))}</span></div>')
    for warning in p.get("warnings") or []:
        rows.append('<div class="bs-row"><span class="bs-dot bs-warn"></span>'
                    f'<span class="bs-t">⚠️ {_esc(warning)}</span></div>')
    evolution = p.get("evolution")
    if evolution:
        if evolution.get("baseline_round") is None:
            rows.append('<div class="bs-row"><span class="bs-dot bs-info"></span>'
                        '<span class="bs-t">🧬 本輪為首次產生的建議</span></div>')
        elif not evolution.get("changed"):
            rows.append('<div class="bs-row"><span class="bs-dot bs-pass"></span>'
                        f'<span class="bs-t">🧬 與第 {evolution["baseline_round"]} '
                        '輪建議相比：不變</span></div>')
        else:
            diff_html = ""
            if evolution.get("sql_diff") is not None:
                for key, title in (("sql_diff", "Join SQL 演進"),
                                   ("ddl_diff", "未來 DDL 演進")):
                    if evolution.get(key):
                        diff_html += (f'<details><summary>{title}</summary>'
                                      f'<pre class="diff">{_esc(evolution[key])}'
                                      '</pre></details>')
            rows.append('<div class="bs-row"><span class="bs-dot bs-warn"></span>'
                        f'<span class="bs-title">🧬 與第 '
                        f'{evolution["baseline_round"]} 輪建議相比：已演進</span>'
                        '<span class="bs-t">點下方展開 diff</span></div>'
                        + diff_html)
    rows.append(f'<details open><summary>建議 Join SQL</summary>'
                f'<pre class="diff">{_esc(p["join_sql"])}</pre></details>')
    rows.append(f'<details open><summary>未來 DDL（建議：'
                f'{_esc(p["table_name"])}）</summary>'
                f'<pre class="diff">{_esc(p["proposed_ddl"])}</pre></details>')
    table_rows = []
    for c in p.get("comparison") or []:
        located = _esc("、".join(c["in_input"])) if c["in_input"] else \
            '<span style="color:var(--bad)">❌ input 未包含</span>'
        table_rows.append(
            f'<tr><td class="mono">{_esc(c["column"])}</td>'
            f'<td class="mono">{_esc(c["type"])}</td>'
            f'<td class="mono">{_esc(c["from_entity"])}</td>'
            f'<td>{located}</td></tr>')
    rows.append(
        '<details open><summary>與 input DDL 的逐欄對比</summary>'
        '<table><thead><tr><th>建議欄位</th><th>型別</th><th>來源 entity</th>'
        '<th>input 落點</th></tr></thead><tbody>'
        + "".join(table_rows) + "</tbody></table></details>")
    input_only = p.get("input_only") or []
    if input_only:
        rows.append('<div class="bs-row"><span class="bs-dot bs-info"></span>'
                    f'<span class="bs-t">input 獨有欄位（建議模型未涵蓋，'
                    f'{len(input_only)}）：'
                    + _esc("、".join(f"{c['table']}.{c['column']}"
                                     for c in input_only))
                    + '</span></div>')
    return _card('建議 DDL 對比<span class="bs-hint">（依參考模型自動組建；'
                 '建議值，不影響判定；每輪隨 input 演進）</span>',
                 "".join(rows))


def _derivation_html(meta: dict) -> str:
    """衍生 SQL 對照卡片：你的 Join SQL＋三方鍵矩陣＋欄位覆蓋。"""
    d = meta.get("derivation")
    if not d:
        return ""
    rows = ['<div class="bs-row"><span class="bs-t">基底表 '
            f'<span class="mono">{_esc(d["base_table"])}</span> · 來源表：'
            f'{_esc("、".join(d["source_tables"]))} · join {d["join_count"]} 組 · '
            f'輸出欄 {d["output_count"]}</span></div>']
    cov = d.get("coverage")
    if cov:
        issues = []
        if cov["missing_in_sql"]:
            issues.append(f"DDL 有但 SQL 沒產出 {cov['missing_in_sql']}")
        if cov["extra_in_sql"]:
            issues.append(f"SQL 產出但 DDL 沒有 {cov['extra_in_sql']}")
        css = "bs-warn" if issues else "bs-pass"
        rows.append(f'<div class="bs-row"><span class="bs-dot {css}"></span>'
                    f'<span class="bs-t">寬表 <span class="mono">'
                    f'{_esc(cov["wide_table"])}</span> 欄位覆蓋 '
                    f'{cov["covered"]}/{cov["ddl_columns"]}'
                    + (f'；{_esc("；".join(issues))}' if issues else "")
                    + '</span></div>')
    rows.append(f'<details><summary>你的 Join SQL</summary>'
                f'<pre class="diff">{_esc(d["sql"])}</pre></details>')
    matrix = d.get("key_matrix") or []
    if matrix:
        head = "<tr><th>join 鍵</th><th>你的 SQL</th><th>relations.yaml</th>"
        if d.get("has_proposal"):
            head += "<th>建議 SQL</th>"
        head += "</tr>"
        body = []
        for row in matrix:
            cells = (f'<td class="mono">{_esc(row["pair"])}</td>'
                     f'<td>{"✅" if row["in_sql"] else "❌"}</td>'
                     f'<td>{"✅" if row["in_relations"] else "❌"}</td>')
            if d.get("has_proposal"):
                cells += f'<td>{"✅" if row["in_proposal"] else "❌"}</td>'
            body.append(f"<tr>{cells}</tr>")
        rows.append('<details open><summary>join 鍵三方對照</summary>'
                    f'<table><thead>{head}</thead><tbody>'
                    + "".join(body) + "</tbody></table></details>")
    return _card(f'衍生 SQL 對照<span class="bs-hint">（input/<名>/{_esc(d["file"])}'
                 '——你的實際 Join 對照宣告關聯與建議 SQL）</span>',
                 "".join(rows))


def _advisory_state_html(meta: dict, findings: list[Finding]) -> str:
    """Describe whether the advisory zone has real suggestions or is pending."""
    pending = [f for f in findings
               if f.zone == ZONE_ADVISORY and f.status == "skipped" and
               (f.source == "llm" or "skipped" in f.message.lower())]
    if meta.get("advisory_merged"):
        return "LLM／語意建議 · 一律提示 · <b>永不影響判定</b> · ✅ 已由 agent 補完"
    if pending:
        return ("LLM／語意建議 · 一律提示 · <b>永不影響判定</b> · "
                "本次未接 LLM，語意規則待補完")
    return "LLM／語意建議 · 一律提示 · <b>永不影響判定</b> · 不保證可重複"


def to_html(findings: list[Finding], meta: dict | None = None) -> str:
    s = summarize(findings)
    meta = meta or {}
    verdict_ok = s["compliant"]
    verdict_txt = "合規" if verdict_ok else "不合規"
    gen = _generated_at()
    domains = "、".join(meta.get("domains_loaded", [])) or "—"
    bundle = (meta.get("validation_manifest") or {}).get(
        "validation_bundle_code", "—")

    # build rows grouped by category
    origins = check_origins(findings, meta)
    cats_html = []
    for cat, title in CATEGORY_TITLES.items():
        cat_f = [f for f in findings if f.category == cat]
        if not cat_f:
            continue
        cat_f.sort(key=lambda f: (f.status != "fail", f.status != "warning",
                                  f.status != "skipped", f.status != "info"))
        n_fail = sum(1 for f in cat_f if f.status == "fail")
        n_warn = sum(1 for f in cat_f if f.status == "warning")
        rows = []
        for f in cat_f:
            zone = "閘門" if f.zone == ZONE_GATING else "顧問"
            rationale = (f'<div class="rationale">理由：{_esc(f.rationale)}</div>'
                         if f.rationale else "")
            if origins.get(f.check_id):
                rationale += (f'<div class="rationale">依據：'
                              f'<span class="mono">{_esc(origins[f.check_id])}'
                              '</span></div>')
            ea = ""
            if f.expected or f.actual:
                ea += (f'<div class="ea"><span class="ea-l">期望</span>{_esc(f.expected)}'
                       f'<span class="ea-l">實際</span><span class="ea-bad">{_esc(f.actual)}</span></div>')
            if f.fix:
                ea += f'<div class="ea"><span class="ea-l">修法</span>{_esc(f.fix)}</div>' 
            rows.append(
                f'<tr class="row" data-status="{f.status}" data-zone="{f.zone}" '
                f'data-source="{_esc(f.source)}" '
                f'data-text="{_esc((f.check_id + " " + f.target + " " + f.message + " " + (f.rationale or "")).lower())}">'
                f'<td class="st st-{f.status}"><span class="dot"></span>{_ICON.get(f.status,"")}</td>'
                f'<td><span class="badge zone-{f.zone}">{zone}</span></td>'
                f'<td class="mono">{_esc(f.check_id)}</td>'
                f'<td class="mono">{_esc(f.target)}</td>'
                f'<td>{_esc(f.message)}{ea}{rationale}</td>'
                f'<td class="src">{_esc(f.source)}</td></tr>')
        # 沒有失敗／警告的分類預設收合——長報告先看得到重點，點標題可展開
        clean = " collapsed" if (n_fail == 0 and n_warn == 0) else ""
        cats_html.append(f"""
        <section class="cat{clean}" data-cat="{cat}">
          <button class="cat-head" onclick="toggleCat(this)">
            <span class="chev">▾</span>
            <span class="cat-title">{_esc(title)}</span>
            <span class="cat-meta">{len(cat_f)} 項{f' · {n_fail} 失敗' if n_fail else ''}{f' · {n_warn} 警告' if n_warn else ''}{' · 已全數通過（點開展開）' if clean else ''}</span>
          </button>
          <div class="cat-body">
            <table>
              <thead><tr><th>狀態</th><th>區</th><th>檢查</th><th>對象</th><th>說明</th><th>來源</th></tr></thead>
              <tbody>{''.join(rows)}</tbody>
            </table>
          </div>
        </section>""")

    verdict_class = "ok" if verdict_ok else "bad"
    round_no = (meta.get("iteration") or {}).get("round")
    max_rounds = (meta.get("iteration") or {}).get("max_rounds", 5)
    round_title = f" — 第 {round_no} 輪迭代" if round_no else ""
    round_badge = (f' <span class="badge zone-gating" style="font-size:14px;'
                   f'vertical-align:middle">🔁 第 {round_no}／{max_rounds} 輪</span>'
                   if round_no else "")
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>資料設計驗證報告{round_title}</title>
<style>
  :root {{
    --bg:#f6f7f9; --card:#fff; --ink:#1d2127; --muted:#6b7280; --line:#e5e7eb;
    --ok:#15803d; --ok-bg:#dcfce7; --bad:#b91c1c; --bad-bg:#fee2e2;
    --warn:#b45309; --warn-bg:#fef3c7; --info:#1d4ed8; --info-bg:#dbeafe;
    --gating:#374151; --advisory:#7c3aed;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0f1115; --card:#171a21; --ink:#e6e8ec; --muted:#9aa0aa; --line:#2a2f3a; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,"Segoe UI","Microsoft JhengHei",sans-serif; line-height:1.6; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:24px 18px 64px; }}
  h1 {{ font-size:22px; font-weight:600; margin:0 0 4px; }}
  .sub {{ color:var(--muted); font-size:13px; margin-bottom:18px; }}
  .verdict {{ display:inline-flex; align-items:center; gap:8px; font-size:18px;
    font-weight:600; padding:8px 16px; border-radius:10px; }}
  .verdict.ok {{ color:var(--ok); background:var(--ok-bg); }}
  .verdict.bad {{ color:var(--bad); background:var(--bad-bg); }}
  .cards {{ display:flex; flex-wrap:wrap; gap:10px; margin:16px 0 8px; }}
  .kpi {{ flex:1; min-width:96px; background:var(--card); border:1px solid var(--line);
    border-radius:10px; padding:10px 14px; }}
  .kpi .n {{ font-size:20px; font-weight:600; }}
  .kpi .l {{ font-size:12px; color:var(--muted); }}
  .meta {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
    padding:10px 14px; font-size:13px; color:var(--muted); margin:8px 0 18px; }}
  .controls {{ position:sticky; top:0; background:var(--bg); padding:10px 0;
    display:flex; flex-wrap:wrap; gap:8px; align-items:center; z-index:5; border-bottom:1px solid var(--line); }}
  .controls input[type=search] {{ flex:1; min-width:180px; padding:8px 12px;
    border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--ink); font-size:14px; }}
  .chip {{ padding:6px 12px; border:1px solid var(--line); border-radius:999px;
    background:var(--card); color:var(--ink); font-size:13px; cursor:pointer; user-select:none; }}
  .chip.active {{ background:var(--ink); color:var(--bg); border-color:var(--ink); }}
  .cat {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    margin:14px 0; overflow:hidden; }}
  .cat-head {{ width:100%; text-align:left; background:none; border:none; color:var(--ink);
    padding:14px 16px; font-size:15px; cursor:pointer; display:flex; align-items:center; gap:10px; }}
  .cat-title {{ font-weight:600; }}
  .cat-meta {{ color:var(--muted); font-size:13px; margin-left:auto; }}
  .chev {{ transition:transform .15s; font-size:12px; color:var(--muted); }}
  .cat.collapsed .chev {{ transform:rotate(-90deg); }}
  .cat.collapsed .cat-body {{ display:none; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; table-layout:fixed; }}
  th, td {{ text-align:left; padding:9px 12px; border-top:1px solid var(--line); vertical-align:top;
    overflow-wrap:anywhere; word-break:break-word; }}
  th {{ color:var(--muted); font-weight:500; font-size:12px; }}
  /* 固定欄寬：說明欄拿走剩餘空間；長識別字／清單在欄內斷行，不溢出 */
  thead th:nth-child(1) {{ width:52px; }}
  thead th:nth-child(2) {{ width:60px; }}
  thead th:nth-child(3) {{ width:16%; }}
  thead th:nth-child(4) {{ width:14%; }}
  thead th:nth-child(6) {{ width:52px; }}
  .mono {{ font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12.5px;
    overflow-wrap:anywhere; }}
  .src {{ color:var(--muted); }}
  .rationale {{ color:var(--muted); font-size:12.5px; margin-top:3px; }}
  .badge {{ font-size:12px; padding:2px 8px; border-radius:999px; white-space:nowrap; }}
  .zone-gating {{ background:var(--info-bg); color:var(--info); }}
  .zone-advisory {{ background:#ede9fe; color:var(--advisory); }}
  .st {{ white-space:nowrap; }}
  .st .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; vertical-align:middle; }}
  .st-fail .dot {{ background:var(--bad); }} .st-warning .dot {{ background:var(--warn); }}
  .st-pass .dot {{ background:var(--ok); }} .st-info .dot {{ background:var(--info); }}
  .st-skipped .dot {{ background:var(--muted); }}
  .empty {{ display:none; text-align:center; color:var(--muted); padding:30px; }}
  .hidden {{ display:none !important; }}
  .zones {{ display:flex; flex-wrap:wrap; gap:10px; margin:4px 0 12px; }}
  .zone-box {{ flex:1; min-width:280px; display:flex; align-items:center; gap:8px;
    background:var(--card); border:1px solid var(--line); border-radius:10px;
    padding:10px 14px; font-size:13px; color:var(--muted); }}
  .zone-box.zone-g {{ border-left:3px solid var(--info); }}
  .zone-box.zone-a {{ border-left:3px solid var(--advisory); }}
  .bsum {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:12px 16px; margin:14px 0 4px; }}
  .bs-head {{ font-weight:600; font-size:14px; margin-bottom:8px;
    cursor:pointer; display:flex; align-items:baseline; gap:8px; user-select:none; }}
  .bs-head .chev {{ transition:transform .15s; font-size:12px; color:var(--muted); flex:none; }}
  .bsum.collapsed .bs-head {{ margin-bottom:0; }}
  .bsum.collapsed .bs-head .chev {{ transform:rotate(-90deg); }}
  .bsum.collapsed .bs-body {{ display:none; }}
  pre.diff {{ background:var(--bg); border:1px solid var(--line); border-radius:8px;
    padding:10px 12px; font-size:12px; overflow-x:auto; max-height:320px; }}
  details summary {{ cursor:pointer; font-size:12.5px; padding:4px 0; }}
  .bs-hint {{ color:var(--muted); font-weight:400; font-size:12px; margin-left:6px; }}
  .bs-row {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:8px;
    padding:6px 0; border-top:1px solid var(--line); font-size:13.5px; }}
  .bs-dot {{ width:8px; height:8px; border-radius:50%; flex:none; align-self:center; }}
  .bs-fail {{ background:var(--bad); }} .bs-warn {{ background:var(--warn); }}
  .bs-pass {{ background:var(--ok); }} .bs-info {{ background:var(--info); }}
  .bs-advisory {{ background:var(--advisory); }}
  .bs-rule {{ color:var(--info); text-decoration:none; font-size:12.5px;
    overflow-wrap:anywhere; }}
  .bs-rule:hover {{ text-decoration:underline; }}
  .bs-title {{ font-weight:600; overflow-wrap:anywhere; min-width:0; }}
  .bs-t {{ color:var(--muted); font-size:12.5px; overflow-wrap:anywhere; min-width:0; }}
  .ea {{ font-size:12.5px; margin-top:4px; display:flex; flex-wrap:wrap; gap:4px 8px; align-items:baseline; }}
  .ea > * {{ overflow-wrap:anywhere; min-width:0; }}
  .ea-l {{ color:var(--muted); font-size:11.5px; border:1px solid var(--line); border-radius:4px; padding:0 5px; flex:none; }}
  .ea-bad {{ color:var(--bad); }}
</style>
</head>
<body>
<div class="wrap">
  <h1>資料設計驗證報告{round_badge}</h1>
  <div class="sub">產生時間 {gen}</div>
  <div class="verdict {verdict_class}">{'✅' if verdict_ok else '❌'} 判定：{verdict_txt}（會擋項目 {s['blocking_count']}）</div>

  {_checking_rule_summary_html(findings, meta)}
  {_rule_coverage_html(meta, findings)}
  {_iteration_html(meta)}
  {_proposal_html(meta)}
  {_derivation_html(meta)}
  {_blocking_summary_html(findings)}

  <div class="cards">
    <div class="kpi"><div class="n">{s['fail']}</div><div class="l">失敗</div></div>
    <div class="kpi"><div class="n">{s['warning']}</div><div class="l">警告</div></div>
    <div class="kpi"><div class="n">{s['pass']}</div><div class="l">通過</div></div>
    <div class="kpi"><div class="n">{s['info']}</div><div class="l">提示</div></div>
    <div class="kpi"><div class="n">{s['skipped']}</div><div class="l">略過</div></div>
    <div class="kpi"><div class="n">{s['gating']}</div><div class="l">閘門區</div></div>
    <div class="kpi"><div class="n">{s['advisory']}</div><div class="l">顧問區</div></div>
  </div>
  <div class="meta">方言 {_esc(meta.get('dialect','—'))} · 表數 {_esc(meta.get('tables','—'))}
    · 載入 skill {_esc(meta.get('skills_loaded',0))} 條 · domain：{_esc(domains)}
    · 驗證 bundle：<span class="mono">{_esc(bundle)}</span>
    <br><span style="color:var(--muted)">合規結果直接以 checking rule ID 呈現，不使用指紋或結果碼。</span></div>

  <div class="zones">
    <div class="zone-box zone-g">
      <span class="badge zone-gating">閘門區</span>
      <span>確定性檢查 · <b>決定合規判定</b> · 結果以 checking rule ID 呈現</span>
    </div>
    <div class="zone-box zone-a">
      <span class="badge zone-advisory">顧問區</span>
      <span>{_advisory_state_html(meta, findings)}</span>
    </div>
  </div>

  {_lineage_html(meta)}

  <div class="controls">
    <input type="search" id="q" placeholder="搜尋檢查、對象、說明…" oninput="applyFilters()">
    <span class="chip active" data-f="status" data-v="all" onclick="pick(this)">全部</span>
    <span class="chip" data-f="status" data-v="fail" onclick="pick(this)">只看失敗</span>
    <span class="chip" data-f="status" data-v="warning" onclick="pick(this)">只看警告</span>
    <span class="chip" data-f="zone" data-v="gating" onclick="pick(this)">只看閘門區</span>
    <span class="chip" data-f="zone" data-v="advisory" onclick="pick(this)">只看顧問區</span>
  </div>

  {''.join(cats_html)}
  <div class="empty" id="empty">沒有符合篩選條件的項目。</div>
</div>
<script>
  var F = {{ status:"all", zone:"all" }};
  function pick(el) {{
    var f = el.dataset.f, v = el.dataset.v;
    // toggle: clicking active zone resets to all
    if (f === "status") {{
      document.querySelectorAll('.chip[data-f=status]').forEach(c=>c.classList.remove('active'));
      el.classList.add('active'); F.status = v;
    }} else {{
      var was = el.classList.contains('active');
      document.querySelectorAll('.chip[data-f=zone]').forEach(c=>c.classList.remove('active'));
      if (was) {{ F.zone = "all"; }} else {{ el.classList.add('active'); F.zone = v; }}
    }}
    applyFilters();
  }}
  function applyFilters() {{
    var q = document.getElementById('q').value.trim().toLowerCase();
    var active = q !== "" || F.status !== "all" || F.zone !== "all";
    var shown = 0;
    document.querySelectorAll('section.cat').forEach(function(sec) {{
      var vis = 0;
      sec.querySelectorAll('tr.row').forEach(function(r) {{
        var ok = true;
        if (F.status !== "all" && r.dataset.status !== F.status) ok = false;
        if (F.zone !== "all" && r.dataset.zone !== F.zone) ok = false;
        if (q && r.dataset.text.indexOf(q) === -1) ok = false;
        r.classList.toggle('hidden', !ok);
        if (ok) vis++;
      }});
      sec.classList.toggle('hidden', vis === 0);
      // 篩選中自動展開收合的分類，命中的列才看得到
      if (active && vis > 0) sec.classList.remove('collapsed');
      shown += vis;
    }});
    document.getElementById('empty').style.display = shown === 0 ? 'block' : 'none';
  }}
  function toggleCat(btn) {{ btn.parentElement.classList.toggle('collapsed'); }}
  function toggleCard(el) {{ el.parentElement.classList.toggle('collapsed'); }}
  function filterRule(rule) {{
    var q = document.getElementById('q');
    q.value = rule.toLowerCase();
    applyFilters();
    q.scrollIntoView({{behavior:'smooth', block:'start'}});
  }}
</script>
</body>
</html>"""
