"""SSOT 未登錄主體推斷 — 確定性啟發層（閘門區、警告不擋）。

啟發式（純規則，同輸入必同結果）：
  一張表若 (1) 單一主鍵形如 X_id，(2) X 經字典正規化後不在 registry，
  (3) 表上有 X 的描述性屬性或至少兩個非鍵非 audit 欄位（顯示它「擁有」而非引用），
  則判定為「未登錄主體候選」→ 發 warning 提醒先登錄，放行。

語意確認（是否真為新權威、registry 草稿）留給顧問區/agent，
人工確認後寫回 registry —— registry 從前提變成產物。
"""
from __future__ import annotations
import re
from .model import Schema, Finding, ZONE_GATING

_AUDIT = {"created_at", "updated_at", "created_by", "updated_by", "deleted_at"}


def _norm(tok: str, glossary: dict) -> str:
    tok = tok.lower()
    aliases = {k.lower(): str(v).lower() for k, v in (glossary.get("aliases") or {}).items()}
    banned = {k.lower(): str(v).lower() for k, v in (glossary.get("banned_terms") or {}).items()}
    return aliases.get(tok, banned.get(tok, tok))


def run(schema: Schema, cfg: dict, glossary: dict | None = None):
    """Returns (findings, candidates). candidates 供 advisory prompt 產 registry 草稿。"""
    glossary = glossary or {}
    registry = (cfg.get("ssot") or {}).get("registry") or {}
    known = {e.lower() for e in registry.keys()}
    for m in registry.values():
        k = (m.get("key") or "")
        if k.endswith("_id"):
            known.add(_norm(k[:-3], glossary))

    findings: list[Finding] = []
    candidates: list[dict] = []
    for t in schema.tables:
        if len(t.business_key) != 1 or not t.business_key[0].endswith("_id"):
            continue
        ent = _norm(t.business_key[0][:-3], glossary)
        if not ent or ent in known:
            continue
        attrs = [c.name for c in t.columns
                 if c.name not in t.business_key and c.name not in _AUDIT
                 and not c.name.endswith("_id")]
        ent_attrs = [a for a in attrs
                     if _norm(re.split(r"[_\s]+", a)[0], glossary) == ent]
        evidence = ent_attrs or attrs[:3]
        if not (ent_attrs or len(attrs) >= 2):
            continue
        candidates.append({"entity": ent, "table": t.name, "evidence": evidence})
        findings.append(Finding(
            "SSOT.UNREGISTERED_SUBJECT", "ssot", "warning", t.name,
            f"未登錄主體候選 '{ent}'：此表看似其權威表（證據欄位 {evidence}），"
            f"但 SSOT registry 尚未登錄。建議先登錄再上線。",
            severity="warning",
            rationale="新 data subject 應先登錄權威表，否則跨域 SSOT 硬檢查無法涵蓋它。"
                      "可由顧問區產 registry 草稿、人工確認後寫回。",
            expected=f"'{ent}' 已登錄於 ssot.registry", actual="registry 查無此主體",
            fix=f"於 config/default.yaml 的 ssot.registry 登錄 '{ent}'（權威表 {t.name}）",
            source="rule", zone=ZONE_GATING))
    if not findings:
        findings.append(Finding("SSOT.UNREGISTERED_SUBJECT", "ssot", "pass", "(schema)",
                                "未發現未登錄主體候選。", severity="info",
                                source="rule", zone=ZONE_GATING))
    return findings, candidates
