"""迭代問答（Q&A Loop）：answers.yaml 載入、主題比對、收斂計算。

Phase 1 的硬邊界：answers.yaml **只**流向顧問區 prompt 與報告呈現，
永不進入閘門執行路徑。閘門要變，唯一途徑是使用者手動修改三件權威輸入
（<名>.sql / relations.yaml / context.md）。architecture test 守住這條保證。

問題母體（要收斂的集合）＝顧問區中 source=llm 的實質提問
（CONCEPT.SUBJECT、NAME.SEMANTIC、各 domain check-llm skill 建議）。
「未發現建議」「未取得可解析結果」等空結果標記不是問題，會被濾除。

問題 ID（主題鍵）＝ `<check_id>@<target>`。LLM 每輪措辭會漂，
所以回答是「答主題，不是答字面」：同一 (check_id, target) 的所有提問
視為同一題；比對含表名前綴的寬鬆規則（答 `subscription` 可解
`subscription.start_dt` 的同規則提問）。

收斂條件（使用者定調）：無待答問題 ＋ 閘門合規；上限 MAX_ROUNDS 輪。
`deferred`（擱置）不計入待答、不擋收斂，但報告永遠列出，不會靜默消失。
"""
from __future__ import annotations

import os

import yaml

from .model import Finding, ZONE_ADVISORY, ZONE_GATING

MAX_ROUNDS = 5
CONVERGENCE_RULE = "no_open_questions_and_gating_compliant"
ANSWER_KINDS = ("semantic", "structural")
ANSWER_STATUSES = ("answered", "deferred")

#: 空結果／診斷類訊息不是「給設計者的提問」，不進問題母體。
_NON_QUESTION_MARKERS = ("未發現建議", "未取得可解析結果", "略過語意卡控",
                         "略過主體性概念層")


# ---------------------------------------------------------------- 載入與驗證

def locate(ddl_path: str) -> str:
    """answers.yaml 放在 subject 資料夾（與三件必備同層）；
    舊式平鋪相容 <名>.answers.yaml。固定檔名優先。"""
    base_dir = os.path.dirname(os.path.abspath(ddl_path))
    name = os.path.splitext(os.path.basename(ddl_path))[0]
    fixed = os.path.join(base_dir, "answers.yaml")
    return fixed if os.path.exists(fixed) else os.path.join(
        base_dir, f"{name}.answers.yaml")


def load_answers(path: str) -> tuple[dict | None, list[str]]:
    """讀取並驗證 answers.yaml。回傳 (parsed, problems)。

    選填件的壞檔處理比照 SYSTEM.CONFIG_SPEC 慣例：永不擋報告。
    整檔壞（YAML 錯誤／根節點不是 mapping）→ (None, [原因])，該檔整份略過；
    個別條目壞 → 跳過該條並記 problem，其餘照常生效。
    """
    if not os.path.isfile(path):
        return None, []
    label = os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError("根節點必須是 mapping")
    except Exception as error:
        return None, [f"{label} 無法使用（整份略過）：{type(error).__name__}: {error}"]

    problems: list[str] = []
    iteration = data.get("iteration", 1)
    if not isinstance(iteration, int) or iteration < 1:
        problems.append(f"{label}: iteration 必須是 ≥1 的整數，改用 1")
        iteration = 1

    raw_answers = data.get("answers")
    if raw_answers is None:
        raw_answers = []
    if not isinstance(raw_answers, list):
        problems.append(f"{label}: answers 必須是清單（整份略過）")
        return {"iteration": iteration, "answers": []}, problems

    entries: list[dict] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_answers, start=1):
        where = f"{label} 第 {index} 條"
        if not isinstance(item, dict):
            problems.append(f"{where}：必須是 mapping，已跳過")
            continue
        answer_id = str(item.get("id") or "").strip()
        if "@" not in answer_id:
            problems.append(f"{where}：id 必須是 <check_id>@<target> 格式，已跳過")
            continue
        status = str(item.get("status") or "answered").strip()
        if status not in ANSWER_STATUSES:
            problems.append(f"{where}：status 必須是 {ANSWER_STATUSES}，已跳過")
            continue
        kind = str(item.get("kind") or "semantic").strip()
        if kind not in ANSWER_KINDS:
            problems.append(f"{where}：kind 必須是 {ANSWER_KINDS}，已跳過")
            continue
        answer_text = str(item.get("answer") or "").strip()
        if status == "answered" and not answer_text:
            problems.append(f"{where}：status=answered 但 answer 是空的，已跳過")
            continue
        if answer_id in seen_ids:
            problems.append(f"{where}：id 重複 {answer_id}，已跳過")
            continue
        seen_ids.add(answer_id)
        entries.append({
            "id": answer_id,
            "question": str(item.get("question") or "").strip(),
            "answer": answer_text,
            "kind": kind,
            "status": status,
            "applied_to": str(item.get("applied_to") or "").strip(),
        })
    return {"iteration": iteration, "answers": entries}, problems


def load_for_ddl(ddl_path: str) -> tuple[dict | None, list[str]]:
    return load_answers(locate(ddl_path))


# ---------------------------------------------------------------- 主題比對

def _split_topic(topic_id: str) -> tuple[str, str]:
    check_id, _, target = topic_id.partition("@")
    return check_id.strip(), target.strip()


def _table_of(target: str) -> str:
    return target.split(".", 1)[0]


def topic_matches(answer_id: str, check_id: str, target: str) -> bool:
    """答案主題是否覆蓋這個 finding 主題。

    規則：check_id 必須相同；target 完全相同，或（表名前綴寬鬆）
    其中一方等於另一方的表名部分——答 `subscription` 可解
    `subscription.start_dt` 的同規則提問，反之亦然。"""
    a_check, a_target = _split_topic(answer_id)
    if a_check != check_id:
        return False
    if a_target == target:
        return True
    return (a_target == _table_of(target)) or (target == _table_of(a_target))


# ---------------------------------------------------------------- 問題萃取

def _is_question(f: Finding) -> bool:
    if f.zone != ZONE_ADVISORY or f.source != "llm":
        return False
    if f.status != "info" or not (f.message or "").strip():
        return False
    return not any(marker in f.message for marker in _NON_QUESTION_MARKERS)


def _is_advisory_pending(f: Finding) -> bool:
    return f.zone == ZONE_ADVISORY and f.source == "llm" and f.status == "skipped"


def question_topics(findings: list[Finding]) -> list[dict]:
    """顧問區 findings → 去重後的問題主題清單（保 findings 排序）。"""
    topics: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for f in findings:
        if not _is_question(f):
            continue
        key = (f.check_id, f.target)
        if key in seen:
            continue
        seen.add(key)
        topics.append({"id": f"{f.check_id}@{f.target}",
                       "check_id": f.check_id, "target": f.target,
                       "question": f.message.strip()})
    return topics


# ---------------------------------------------------------------- 收斂計算

def iteration_summary(findings: list[Finding], answers: dict | None,
                      problems: list[str] | None = None,
                      answers_file: str = "") -> dict:
    """算出迭代區塊（meta["iteration"]）。純函式、確定性。"""
    answers = answers or {"iteration": 1, "answers": []}
    entries = answers.get("answers") or []
    topics = question_topics(findings)
    advisory_pending = any(_is_advisory_pending(f) for f in findings)
    gating_fails = sum(1 for f in findings
                       if f.zone == ZONE_GATING and f.status == "fail"
                       and f.severity == "error")

    resolved = [e for e in entries if e["status"] == "answered"]
    deferred = [e for e in entries if e["status"] == "deferred"]

    def covered(topic: dict) -> bool:
        return any(topic_matches(e["id"], topic["check_id"], topic["target"])
                   for e in resolved + deferred)

    open_topics = [t for t in topics if not covered(t)]
    round_no = answers.get("iteration", 1)
    converged = (not advisory_pending and not open_topics and gating_fails == 0)
    return {
        "round": round_no,
        "max_rounds": MAX_ROUNDS,
        "converged": converged,
        "convergence_rule": CONVERGENCE_RULE,
        "advisory_pending": advisory_pending,
        "blockers": {"open_questions": len(open_topics),
                     "gating_fails": gating_fails},
        "open": open_topics,
        "answered": [{"id": e["id"], "kind": e["kind"],
                      "applied_to": e["applied_to"],
                      "question": e["question"], "answer": e["answer"]}
                     for e in resolved],
        "deferred": [{"id": e["id"], "question": e["question"],
                      "answer": e["answer"]} for e in deferred],
        "answers_file": answers_file,
        "answers_problems": list(problems or []),
    }


def clarified_text(answers: dict | None) -> str:
    """已答條目 → 餵給顧問區 LLM prompt 的「已澄清事項」文字。空字串＝無。"""
    entries = [e for e in (answers or {}).get("answers") or []
               if e["status"] == "answered"]
    if not entries:
        return ""
    lines = []
    for e in entries:
        q = f" Q: {e['question']}" if e["question"] else ""
        lines.append(f"- {e['id']}:{q} → A: {e['answer']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- 草稿產出

def draft_yaml(iteration: dict, name: str) -> str:
    """answers_draft.yaml 骨架（確定性）。suggested_answer 由 agent 補填後，
    agent 在對話中逐題向使用者提問；回寫 input/<名>/answers.yaml 的每一筆
    都必須出自使用者在對話中的明確回覆（agent 代筆、使用者作答）。"""
    round_no = iteration.get("round", 1)
    lines = [
        f"# 第 {round_no} 輪草稿 — agent 逐題向使用者提問，依回覆回寫"
        f" input/{name}/answers.yaml",
        "# suggested_* 為 agent 草擬的參考選項；使用者可接受、修改或擱置。",
        "# 回寫時 suggested_answer → answer、suggested_kind → kind",
        "#（structural 請先由使用者手動修改權威輸入並記 applied_to）。",
        f"iteration: {round_no}",
        "open_questions:",
    ]
    open_topics = iteration.get("open") or []
    if not open_topics:
        lines[-1] = "open_questions: []   # 本輪無待答問題"
    for topic in open_topics:
        lines.append(f"  - id: {topic['id']}")
        lines.append("    question: " + _yaml_str(topic["question"]))
        lines.append('    suggested_answer: ""   # ← agent 草擬、使用者審')
        lines.append("    suggested_kind: semantic   # semantic | structural")
        lines.append('    suggested_applied_to: ""   # structural 時建議改哪個權威檔')
    answered = iteration.get("answered") or []
    if answered:
        lines.append("answered:   # 已在 answers.yaml 的主題（確認有被吃到）")
        for e in answered:
            lines.append(f"  - {e['id']}")
    else:
        lines.append("answered: []")
    return "\n".join(lines) + "\n"


def _yaml_str(text: str) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'
