"""自動產生 data subject 的摘要與用途。

每次跑完 data governance 流程後，為這份設計產生一段「摘要 + 用途」，
作為放入 production 前的說明文件。摘要是確定性彙整（表/欄位/鍵/domain），
用途若有 LLM 可補一段語意描述；沒有 LLM 則留結構化摘要。
"""
from __future__ import annotations
from .model import Schema
from .llm import LLMClient, NullLLM


def build_summary(schema: Schema, domains: list[str] | None,
                  compliant: bool, llm: LLMClient | None = None) -> str:
    llm = llm or NullLLM()
    lines = []
    lines.append("# Data Subject 摘要")
    lines.append("")
    lines.append(f"- 合規狀態：{'✅ 通過' if compliant else '❌ 未通過（修正後再納入 production）'}")
    lines.append(f"- 關聯 domain：{', '.join(domains) if domains else '（未指定）'}")
    lines.append(f"- 表數：{len(schema.tables)}")
    lines.append("")
    lines.append("## 結構摘要")
    for t in schema.tables:
        business = ", ".join(t.business_key) or "（無）"
        sorting = ", ".join(t.sorting_key) or "（無）"
        primary = ", ".join(t.primary_key) or "（無）"
        lines.append(f"- **{t.name}**（business key：{business}；sorting key：{sorting}；"
                     f"PRIMARY KEY：{primary}）：" +
                     ", ".join(f"{c.name}:{c.base_type}" for c in t.columns))
    lines.append("")

    # 用途：有 LLM 補語意，否則用結構推斷的提示
    lines.append("## 用途")
    if not isinstance(llm, NullLLM):
        cols = []
        for t in schema.tables:
            cols.append(f"{t.name}: " + ", ".join(c.name for c in t.columns))
        prompt = ("根據以下資料表結構，用 2-3 句話說明這個 data subject 的業務用途與"
                  "它在跨 domain 中扮演的角色。只輸出說明文字。\n" + "\n".join(cols))
        try:
            txt = llm.complete("你是資料治理分析師。", prompt).strip()
            lines.append(txt or "（LLM 未回傳用途說明）")
        except Exception as e:
            lines.append(f"（產生用途說明失敗：{type(e).__name__}: {e}；"
                         "僅保留結構摘要）")
    else:
        lines.append("（未接 LLM：用途說明待補。可由 agent 用其 LLM 依結構摘要補完。）")
    lines.append("")
    return "\n".join(lines)
