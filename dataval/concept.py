"""Advisory upper layer: data-design concept / subject correctness.

This is the independent concept layer in the advisory zone. It asks whether the
ENTITY each table models is right (granularity, relationships), not whether a
single column is correct. Output is phrased as questions for the designer, is
always advisory + info, and never blocks. Requires the LLM; without it, skipped.
"""
from __future__ import annotations
from .model import Schema, Finding, ZONE_ADVISORY
from .llm import LLMClient, NullLLM, call_json

_SYSTEM = (
    "你是資料建模顧問。針對提供的 schema 與情境，只評估『主體性』是否正確："
    "每張表代表的業務主體（entity）是否抓對、粒度是否合理、主體之間的關係建模是否恰當。"
    "不要檢查單一欄位的細節。輸出務必為 JSON 陣列，每個物件含鍵："
    "target（表名）、question（給設計者思考的提問，非結論）、rationale。"
)


def run(schema: Schema, llm: LLMClient | None = None) -> list[Finding]:
    llm = llm or NullLLM()
    if isinstance(llm, NullLLM):
        return [Finding("CONCEPT.SUBJECT", "concept", "skipped", "(schema)",
                        "未設定 LLM，略過主體性概念層。", severity="info",
                        source="llm", zone=ZONE_ADVISORY)]
    brief = [f"情境：{schema.context}"] if schema.context else []
    for t in schema.tables:
        cols = ", ".join(f"{c.name}:{c.base_type}" for c in t.columns)
        brief.append(f"表 {t.name}（business key={t.business_key}、"
                     f"sorting key={t.sorting_key}、PRIMARY KEY={t.primary_key}）：{cols}")
    res = call_json(llm, _SYSTEM, "\n".join(brief))
    out: list[Finding] = []
    if isinstance(res, list):
        for item in res:
            out.append(Finding(
                "CONCEPT.SUBJECT", "concept", "info",
                str(item.get("target", "(schema)")),
                str(item.get("question", "")),
                severity="info", rationale=str(item.get("rationale", "")),
                source="llm", zone=ZONE_ADVISORY))
    else:
        detail = getattr(llm, "last_error", "")
        message = "主體性概念層未取得可解析的 LLM 結果。"
        if detail:
            message += f" 連線診斷：{detail}"
        out.append(Finding("CONCEPT.SUBJECT", "concept", "skipped", "(schema)",
                           message, severity="info", source="llm",
                           zone=ZONE_ADVISORY))
    return out
