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
    }
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


def record_round(history_root: str, subject: str, round_no: int,
                 inputs: dict[str, str], iteration: dict,
                 gating: dict) -> str:
    """寫入本輪快照（內容相同不改寫）並重建 HISTORY.md。"""
    payload = {
        "format": FORMAT,
        "subject": subject,
        "round": round_no,
        "inputs": {label: {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                           "text": text}
                   for label, text in sorted(inputs.items())},
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
