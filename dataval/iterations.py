"""迭代歷史（Q&A Loop 的每輪紀錄）。

iterations/<subject>/round_<N>.json   每輪快照：三件輸入＋answers 全文、
                                      收斂狀態、閘門摘要。內容相同不改寫、
                                      無時間戳——同輪重跑位元組穩定。
iterations/<subject>/HISTORY.md       人讀摘要（每次由 round 檔重建，確定性）。

用途：
  1. 每次回答的問題（answered／proposed／deferred 的主題 ID）逐輪留痕
  2. 報告「迭代收斂」區塊顯示本輪 input 相對前一輪改了什麼
  3. 收斂（最後一輪）時，報告呈現初版 ↔ 終版 input 差異

此模組只做紀錄與 diff，永不回頭影響任何 finding（純報告層）。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re

FORMAT = "dataval.iteration_round.v1"
_ROUND_FILE = re.compile(r"^round_(\d+)\.json$")
#: 初版↔終版 diff 每檔最多呈現的行數（全文快照仍在 round 檔內，不截斷）
DIFF_MAX_LINES = 80


# ---------------------------------------------------------------- 輸入蒐集

def gather_inputs(ddl_path: str) -> dict[str, str]:
    """讀取本輪的文字輸入（DDL／relations／context／answers，存在才收）。"""
    from . import answers as answers_mod
    from .precheck import locate_pieces
    pieces = locate_pieces(ddl_path)
    paths = {
        os.path.basename(ddl_path): ddl_path,
        "relations.yaml": pieces["relations"],
        "context.md": pieces["context"],
        "answers.yaml": answers_mod.locate(ddl_path),
        "derivation.sql": pieces.get("derivation", ""),
    }
    for extra in pieces.get("ddl_extras") or []:   # 多檔 DDL 逐檔追蹤
        paths.setdefault(os.path.basename(extra), extra)
    out: dict[str, str] = {}
    for label, path in paths.items():
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    out[label] = f.read()
            except Exception:
                continue
    return out


# ---------------------------------------------------------------- 快照紀錄

def _write_if_changed(path: str, text: str) -> None:
    """內容相同不改寫——同輪重跑檔案位元組穩定。"""
    old = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def _round_path(history_root: str, subject: str, round_no: int) -> str:
    return os.path.join(history_root, subject, f"round_{round_no}.json")


def _load_round(history_root: str, subject: str, round_no: int) -> dict | None:
    path = _round_path(history_root, subject, round_no)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if data.get("format") == FORMAT else None
    except Exception:
        return None


def _recorded_rounds(history_root: str, subject: str) -> list[int]:
    dirp = os.path.join(history_root, subject)
    if not os.path.isdir(dirp):
        return []
    out = []
    for fn in os.listdir(dirp):
        m = _ROUND_FILE.match(fn)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def compact_findings(findings) -> list[dict]:
    """Finding 物件 → 可入快照、可跨輪比對的精簡形。"""
    return [{"check_id": f.check_id, "target": f.target, "zone": f.zone,
             "status": f.status, "severity": f.severity, "message": f.message}
            for f in findings]


def record_round(history_root: str, subject: str, round_no: int,
                 inputs: dict[str, str], iteration: dict,
                 gating: dict, findings: list[dict] | None = None,
                 proposal: dict | None = None) -> str:
    """寫入本輪快照（內容相同不改寫）並重建 HISTORY.md。"""
    proposal_digest = None
    if proposal:
        proposal_digest = {
            "table_name": proposal.get("table_name", ""),
            "sha256": hashlib.sha256(
                (proposal.get("join_sql", "") + "\n" +
                 proposal.get("proposed_ddl", "")).encode("utf-8")).hexdigest(),
            # 全文入快照——下一輪才能列出建議 SQL／DDL 的演進 diff
            "join_sql": proposal.get("join_sql", ""),
            "proposed_ddl": proposal.get("proposed_ddl", ""),
        }
    payload = {
        "format": FORMAT,
        "subject": subject,
        "round": round_no,
        "inputs": {label: {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                           "text": text}
                   for label, text in sorted(inputs.items())},
        "findings": list(findings or []),
        "proposal": proposal_digest,
        "answers_state": {
            "answered": sorted(e["id"] for e in iteration.get("answered") or []),
            "proposed": sorted(e["id"] for e in iteration.get("proposed") or []),
            "deferred": sorted(e["id"] for e in iteration.get("deferred") or []),
        },
        "converged": bool(iteration.get("converged")),
        "advisory_pending": bool(iteration.get("advisory_pending")),
        "blockers": dict(iteration.get("blockers") or {}),
        "gating": dict(gating or {}),
    }
    dirp = os.path.join(history_root, subject)
    os.makedirs(dirp, exist_ok=True)
    path = _round_path(history_root, subject, round_no)
    old = _load_round(history_root, subject, round_no)
    if old != payload:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)
    _rebuild_history_md(history_root, subject)
    return path


def _rebuild_history_md(history_root: str, subject: str) -> None:
    dirp = os.path.join(history_root, subject)
    lines = [f"# 迭代歷史 — {subject}", "",
             "每輪由 run.py／merge_advisory.py 自動記錄；完整輸入快照見同輪 "
             "`round_<N>.json`。", ""]
    rounds = _recorded_rounds(history_root, subject)
    for n in rounds:
        data = _load_round(history_root, subject, n)
        if not data:
            continue
        state = "✅ 已收斂" if data.get("converged") else "❌ 未收斂"
        blockers = data.get("blockers") or {}
        answers_state = data.get("answers_state") or {}
        lines.append(f"## 第 {n} 輪 ｜ {state}")
        lines.append(
            f"- 待答 {blockers.get('open_questions', 0)}、"
            f"待驗證 {blockers.get('proposed_unverified', 0)}、"
            f"閘門 fail {blockers.get('gating_fails', 0)}")
        for key, label in (("answered", "已答"), ("proposed", "代填待驗證"),
                           ("deferred", "擱置")):
            ids = answers_state.get(key) or []
            if ids:
                lines.append(f"- {label}：" + "、".join(f"`{x}`" for x in ids))
        prev = _load_round(history_root, subject, n - 1)
        if prev:
            changed = [label for label, meta in (data.get("inputs") or {}).items()
                       if (prev.get("inputs") or {}).get(label, {}).get("sha256")
                       != meta.get("sha256")]
            added = [label for label in (data.get("inputs") or {})
                     if label not in (prev.get("inputs") or {})]
            note = "、".join(sorted(set(changed) - set(added))) or "（無）"
            lines.append(f"- input 變更（vs 第 {n - 1} 輪）：{note}"
                         + (f"；新增 {'、'.join(added)}" if added else ""))
            delta = _delta_between(prev.get("findings") or [],
                                   data.get("findings") or [])
            lines.append(f"- 發現變化（vs 第 {n - 1} 輪）："
                         f"新增 {len(delta['new'])}、解決 {len(delta['resolved'])}、"
                         f"狀態變化 {len(delta['changed'])}"
                         f"（明細：round_{n}.delta.md）")
            cur_p, prev_p = data.get("proposal"), prev.get("proposal")
            if cur_p:
                changed_note = ("首次產生" if not prev_p else
                                "不變" if cur_p.get("sha256") ==
                                prev_p.get("sha256") else "已演進")
                lines.append(f"- 建議 DDL（{cur_p.get('table_name', '?')}）："
                             f"{changed_note}（round_{n}.proposal.md；拆檔 "
                             f"round_{n}.join.sql／round_{n}.future.ddl）")
        lines.append("")
    text = "\n".join(lines)
    path = os.path.join(dirp, "HISTORY.md")
    old = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


# ---------------------------------------------------------------- 變更與差異

def _line_delta(before: str, after: str) -> tuple[int, int]:
    added = removed = 0
    for line in difflib.ndiff(before.splitlines(), after.splitlines()):
        if line.startswith("+ "):
            added += 1
        elif line.startswith("- "):
            removed += 1
    return added, removed


def input_changes(history_root: str, subject: str, round_no: int,
                  inputs: dict[str, str]) -> dict:
    """本輪 input 相對「前一個有紀錄的輪」改了什麼。首輪回 baseline None。"""
    prior = [n for n in _recorded_rounds(history_root, subject) if n < round_no]
    if not prior:
        return {"baseline_round": None, "files": []}
    baseline_no = max(prior)
    baseline = _load_round(history_root, subject, baseline_no) or {}
    base_inputs = {label: meta.get("text", "")
                   for label, meta in (baseline.get("inputs") or {}).items()}
    files = []
    for label in sorted(set(base_inputs) | set(inputs)):
        if label not in base_inputs:
            files.append({"file": label, "status": "added"})
        elif label not in inputs:
            files.append({"file": label, "status": "removed"})
        elif base_inputs[label] == inputs[label]:
            files.append({"file": label, "status": "unchanged"})
        else:
            added, removed = _line_delta(base_inputs[label], inputs[label])
            files.append({"file": label, "status": "changed",
                          "added": added, "removed": removed})
    return {"baseline_round": baseline_no, "files": files}


def _findings_by_key(items: list[dict]) -> dict:
    grouped: dict[tuple, list[dict]] = {}
    for f in items:
        grouped.setdefault((f.get("check_id"), f.get("target"),
                            f.get("zone")), []).append(f)
    return grouped


def _delta_between(prev: list[dict], current: list[dict]) -> dict:
    """兩輪 findings 的差異：新增／解決／狀態變化（key＝檢查×對象×區）。"""
    before, after = _findings_by_key(prev), _findings_by_key(current)

    def statuses(items):
        return sorted({f.get("status") for f in items})

    new, resolved, changed = [], [], []
    for key in sorted(set(after) - set(before)):
        items = after[key]
        new.append({"check_id": key[0], "target": key[1], "zone": key[2],
                    "statuses": statuses(items),
                    "message": items[0].get("message", "")})
    for key in sorted(set(before) - set(after)):
        items = before[key]
        resolved.append({"check_id": key[0], "target": key[1], "zone": key[2],
                         "statuses": statuses(items),
                         "message": items[0].get("message", "")})
    for key in sorted(set(before) & set(after)):
        b, a = statuses(before[key]), statuses(after[key])
        if b != a:
            changed.append({"check_id": key[0], "target": key[1],
                            "zone": key[2], "before": b, "after": a,
                            "message": after[key][0].get("message", "")})
    return {"new": new, "resolved": resolved, "changed": changed}


def findings_delta(history_root: str, subject: str, round_no: int,
                   current: list[dict]) -> dict:
    """本輪 findings 相對「前一個有紀錄的輪」的變化。首輪 baseline None。"""
    prior = [n for n in _recorded_rounds(history_root, subject) if n < round_no]
    if not prior:
        return {"baseline_round": None, "new": [], "resolved": [], "changed": []}
    baseline_no = max(prior)
    baseline = _load_round(history_root, subject, baseline_no) or {}
    delta = _delta_between(baseline.get("findings") or [], current)
    delta["baseline_round"] = baseline_no
    return delta


_STATUS_ICON = {"fail": "❌", "warning": "⚠️", "pass": "✅",
                "info": "ℹ️", "skipped": "⏭️"}


def _delta_line(entry: dict, statuses_key: str = "statuses") -> str:
    icons = "".join(_STATUS_ICON.get(s, "") for s in entry.get(statuses_key, []))
    msg = (entry.get("message") or "").replace("\n", " ")[:90]
    return (f"- {icons} `{entry['check_id']}` `{entry['target']}`"
            f"（{'閘門' if entry.get('zone') == 'gating' else '顧問'}）：{msg}")


def write_delta_md(history_root: str, subject: str, round_no: int,
                   iteration: dict) -> str:
    """每輪變更報告：只列有改動的地方（round_<N>.delta.md）。"""
    delta = iteration.get("findings_delta") or {}
    changes = iteration.get("input_changes") or {}
    baseline = delta.get("baseline_round")
    lines = [f"# 第 {round_no} 輪迭代變更報告 — {subject}", ""]
    if baseline is None:
        lines.append("首輪——無前輪可比。完整結果見同資料夾 "
                     f"`round_{round_no}.report.md`。")
    else:
        lines.append(f"與**第 {baseline} 輪**相比的變化；完整結果見同資料夾 "
                     f"`round_{round_no}.report.md`。")
        lines.append("")
        lines.append("## 📝 input 變更")
        files = changes.get("files") or []
        changed_files = [f for f in files if f["status"] != "unchanged"]
        if changed_files:
            for f in changed_files:
                if f["status"] == "changed":
                    lines.append(f"- `{f['file']}`：變更（+{f.get('added', 0)}"
                                 f"／−{f.get('removed', 0)} 行）")
                else:
                    lines.append(f"- `{f['file']}`：{f['status']}")
        else:
            lines.append("（無）")
        lines.append("")
        for key, title in (("new", "🆕 新增的發現"),
                           ("resolved", "✅ 解決（消失）的發現"),):
            entries = delta.get(key) or []
            lines.append(f"## {title}（{len(entries)}）")
            lines.extend(_delta_line(e) for e in entries)
            if not entries:
                lines.append("（無）")
            lines.append("")
        entries = delta.get("changed") or []
        lines.append(f"## 🔄 狀態變化（{len(entries)}）")
        for e in entries:
            lines.append(f"- `{e['check_id']}` `{e['target']}`："
                         f"{'／'.join(e['before'])} → {'／'.join(e['after'])}")
        if not entries:
            lines.append("（無）")
    text = "\n".join(lines) + "\n"
    dirp = os.path.join(history_root, subject)
    os.makedirs(dirp, exist_ok=True)
    path = os.path.join(dirp, f"round_{round_no}.delta.md")
    old = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return path


def proposal_evolution(history_root: str, subject: str, round_no: int,
                       proposal: dict | None) -> dict | None:
    """本輪建議 SQL／DDL 相對前一輪建議的演進。首輪回 baseline None。"""
    if not proposal:
        return None
    prior = [n for n in _recorded_rounds(history_root, subject) if n < round_no]
    if not prior:
        return {"baseline_round": None, "changed": False}
    baseline_no = max(prior)
    prev = (_load_round(history_root, subject, baseline_no) or {}
            ).get("proposal") or {}
    if not prev:
        return {"baseline_round": None, "changed": False}   # 前輪無建議＝首次
    cur_sha = hashlib.sha256(
        (proposal.get("join_sql", "") + "\n" +
         proposal.get("proposed_ddl", "")).encode("utf-8")).hexdigest()
    if "join_sql" not in prev:   # 舊格式快照只有雜湊，列不出 diff
        return {"baseline_round": baseline_no,
                "changed": prev.get("sha256") != cur_sha, "sql_diff": None,
                "ddl_diff": None}
    out = {"baseline_round": baseline_no, "changed": False,
           "sql_diff": "", "ddl_diff": "", "truncated": False}
    for key, prev_text, cur_text in (
            ("sql_diff", prev.get("join_sql", ""), proposal.get("join_sql", "")),
            ("ddl_diff", prev.get("proposed_ddl", ""),
             proposal.get("proposed_ddl", ""))):
        if prev_text == cur_text:
            continue
        out["changed"] = True
        lines = list(difflib.unified_diff(
            prev_text.splitlines(), cur_text.splitlines(),
            fromfile=f"第{baseline_no}輪建議", tofile=f"第{round_no}輪建議",
            lineterm=""))
        if len(lines) > DIFF_MAX_LINES:
            out["truncated"] = True
            lines = lines[:DIFF_MAX_LINES]
        out[key] = "\n".join(lines)
    return out


def prune_after_promotion(history_root: str, subject: str) -> tuple[int, int]:
    """晉升後精簡迭代歷史：保留 HISTORY.md（全程摘要）與最終輪的檔案，
    刪除早期輪的全文快照。回傳 (保留輪, 刪除檔案數)。"""
    dirp = os.path.join(history_root, subject)
    rounds = _recorded_rounds(history_root, subject)
    if not rounds:
        return (0, 0)
    latest = max(rounds)
    pattern = re.compile(r"^round_(\d+)(\.report\.md|\.delta\.md"
                         r"|\.proposal\.md|\.join\.sql|\.future\.ddl|\.json)$")
    removed = 0
    for fn in sorted(os.listdir(dirp)):
        m = pattern.match(fn)
        if m and int(m.group(1)) < latest:
            os.remove(os.path.join(dirp, fn))
            removed += 1
    return (latest, removed)


def record_full_round(history_root: str, subject: str, ddl_path: str,
                      meta: dict, findings, gating_summary: dict) -> int:
    """一站式每輪紀錄：計算 input 變更／發現 delta／建議演進 → 注入 meta →
    寫快照與 proposal 存檔。run.py 與 merge_advisory 唯一共用入口
    （merge 端寫入的是該輪權威終態）。回傳輪次。"""
    it = meta.get("iteration") or {}
    round_no = it.get("round", 1)
    inputs = gather_inputs(ddl_path)
    it["input_changes"] = input_changes(history_root, subject, round_no, inputs)
    compact = compact_findings(findings)
    it["findings_delta"] = findings_delta(history_root, subject, round_no, compact)
    if it.get("converged"):
        it["first_last"] = first_last_diff(history_root, subject, round_no, inputs)
    proposal = meta.get("ddl_proposal")
    if proposal:
        proposal["evolution"] = proposal_evolution(
            history_root, subject, round_no, proposal)
    record_round(history_root, subject, round_no, inputs, it, gating_summary,
                 findings=compact, proposal=proposal)
    write_proposal_md(history_root, subject, round_no, proposal)
    write_proposal_files(history_root, subject, round_no, proposal)
    return round_no


def archive_round_outputs(history_root: str, subject: str, round_no: int,
                          report_md: str, iteration: dict) -> None:
    """本輪報告存檔＋變更報告（delta）——與 record_full_round 成對使用。"""
    archive_report(history_root, subject, round_no, report_md)
    write_delta_md(history_root, subject, round_no, iteration)


def proposal_file_texts(subject: str, round_no: int, proposal: dict,
                        proposal_md_ref: str = "") -> dict[str, str]:
    """拆檔內容：{'join.sql': …, 'future.ddl': …}——檔頭標明輪次，
    可直接拿去 SQL 工具使用。proposal_md_ref 是檔頭指向的對照文件位置
    （預設同資料夾的 round_<N>.proposal.md）。"""
    ref = proposal_md_ref or f"round_{round_no}.proposal.md"
    header = (f"-- 第 {round_no} 輪{{what}} — {subject}（自動組建，建議值）\n"
              f"-- 對照與演進 diff 見 {ref}\n\n")
    return {
        "join.sql": header.format(what="建議 Join SQL")
        + proposal.get("join_sql", "").rstrip() + "\n",
        "future.ddl": header.format(what="未來 DDL")
        + proposal.get("proposed_ddl", "").rstrip() + "\n",
    }


def write_proposal_files(history_root: str, subject: str, round_no: int,
                         proposal: dict | None) -> tuple[str, str] | None:
    """建議 Join SQL／未來 DDL 拆檔（round_<N>.join.sql／round_<N>.future.ddl）。

    檔名與檔頭都標明輪次，可直接拿去 SQL 工具使用；
    對照說明與演進 diff 仍在同輪 round_<N>.proposal.md。"""
    if not proposal:
        return None
    dirp = os.path.join(history_root, subject)
    os.makedirs(dirp, exist_ok=True)
    texts = proposal_file_texts(subject, round_no, proposal)
    sql_path = os.path.join(dirp, f"round_{round_no}.join.sql")
    _write_if_changed(sql_path, texts["join.sql"])
    ddl_path = os.path.join(dirp, f"round_{round_no}.future.ddl")
    _write_if_changed(ddl_path, texts["future.ddl"])
    return sql_path, ddl_path


def write_proposal_md(history_root: str, subject: str, round_no: int,
                      proposal: dict | None) -> str | None:
    """每輪的建議 Join SQL＋未來 DDL 存檔（round_<N>.proposal.md，建議值）。"""
    if not proposal:
        return None
    lines = [f"# 第 {round_no} 輪建議 DDL — {subject}（自動組建，建議值）", "",
             f"基底表 `{proposal['base_table']}` · 涵蓋 entity："
             + "、".join(f"`{e}`" for e in proposal.get("entities") or []), "",
             f"📄 拆檔（可直接使用）：`round_{round_no}.join.sql`（建議 Join SQL）、"
             f"`round_{round_no}.future.ddl`（未來 DDL）", ""]
    if proposal.get("not_in_input"):
        lines.append("⚠️ 參考模型有、input 尚未涵蓋："
                     + "、".join(f"`{t}`" for t in proposal["not_in_input"]))
        lines.append("")
    for warning in proposal.get("warnings") or []:
        lines.append(f"⚠️ {warning}")
    if proposal.get("warnings"):
        lines.append("")
    lines += ["## 建議 Join SQL", "```sql", proposal.get("join_sql", ""), "```",
              "", f"## 未來 DDL（`{proposal.get('table_name', '')}`）",
              "```sql", proposal.get("proposed_ddl", ""), "```", ""]
    evolution = proposal.get("evolution")
    if evolution and evolution.get("baseline_round") is not None:
        lines.append(f"## 與第 {evolution['baseline_round']} 輪建議相比")
        if not evolution.get("changed"):
            lines.append("**不變**")
        elif evolution.get("sql_diff") is None:
            lines.append("已演進（前輪快照未存全文，無法列 diff）")
        else:
            for key, title in (("sql_diff", "Join SQL 演進"),
                               ("ddl_diff", "DDL 演進")):
                if evolution.get(key):
                    lines += [f"### {title}", "```diff", evolution[key], "```"]
            if evolution.get("truncated"):
                lines.append("（diff 過長已截斷）")
        lines.append("")
    text = "\n".join(lines)
    dirp = os.path.join(history_root, subject)
    os.makedirs(dirp, exist_ok=True)
    path = os.path.join(dirp, f"round_{round_no}.proposal.md")
    old = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return path


_REPORT_STAMP = re.compile(r"^_產生時間 .*?_<br>$", re.MULTILINE)


def archive_report(history_root: str, subject: str, round_no: int,
                   report_md: str) -> str:
    """把本輪完整報告存檔為 round_<N>.report.md。
    時間戳列改成輪次標示——同輪重跑內容不變時檔案位元組穩定。"""
    text = _REPORT_STAMP.sub(f"_第 {round_no} 輪迭代存檔_<br>", report_md, count=1)
    dirp = os.path.join(history_root, subject)
    os.makedirs(dirp, exist_ok=True)
    path = os.path.join(dirp, f"round_{round_no}.report.md")
    old = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return path


def first_last_diff(history_root: str, subject: str, round_no: int,
                    inputs: dict[str, str]) -> dict | None:
    """初版（第 1 輪）↔ 終版（本輪）的 input 差異。第 1 輪或無初版紀錄回 None。"""
    if round_no <= 1:
        return None
    first = _load_round(history_root, subject, 1)
    if not first:
        return None
    first_inputs = {label: meta.get("text", "")
                    for label, meta in (first.get("inputs") or {}).items()}
    files = []
    for label in sorted(set(first_inputs) | set(inputs)):
        before = first_inputs.get(label, "")
        after = inputs.get(label, "")
        if before == after:
            files.append({"file": label, "status": "unchanged"})
            continue
        status = ("added" if label not in first_inputs else
                  "removed" if label not in inputs else "changed")
        added, removed = _line_delta(before, after)
        diff_lines = list(difflib.unified_diff(
            before.splitlines(), after.splitlines(),
            fromfile=f"第1輪/{label}", tofile=f"第{round_no}輪/{label}",
            lineterm=""))
        truncated = len(diff_lines) > DIFF_MAX_LINES
        files.append({"file": label, "status": status,
                      "added": added, "removed": removed,
                      "diff": "\n".join(diff_lines[:DIFF_MAX_LINES]),
                      "truncated": truncated})
    return {"first_round": 1, "last_round": round_no, "files": files}
