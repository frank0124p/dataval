#!/usr/bin/env python3
"""產生 config 知識庫總索引 → docs/素材索引.generated.md

一份 md 看清整個 config：各域有什麼素材、實體與關係長怎樣、
權威（SSOT）誰屬、所有標記（tag）的意義。內容確定性產生（無時間戳），
config 沒變重跑結果位元組相同。

用法（新增／修改 config 文件後隨時重跑）：
    python config_index.py
"""
from __future__ import annotations

import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from dataval import design as design_mod                      # noqa: E402
from dataval.compiler import ensure_compiled                  # noqa: E402
from dataval.proposal import load_domain_er_full              # noqa: E402

CONFIG_DIR = os.path.join(HERE, "config")
OUT_PATH = os.path.join(HERE, "docs", "素材索引.generated.md")


def _domains(config_dir: str) -> list[str]:
    folders = sorted(f for f in os.listdir(config_dir)
                     if os.path.isdir(os.path.join(config_dir, f))
                     and not f.startswith("_"))
    return (["Common"] if "Common" in folders else []) + \
        [f for f in folders if f != "Common"]


def _ssot(config_dir: str, domain: str) -> dict:
    path = os.path.join(config_dir, domain, "ssot", "registry.yaml")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _rule_counts(compiled_path: str) -> dict[str, dict[str, int]]:
    try:
        with open(compiled_path, encoding="utf-8") as f:
            compiled = json.load(f)
    except Exception:
        return {}
    out: dict[str, dict[str, int]] = {}
    for rule in compiled.get("rules", []):
        d = out.setdefault(rule.get("domain", "Common"),
                           {"gating": 0, "advisory": 0})
        d[rule.get("zone", "gating")] = d.get(rule.get("zone", "gating"), 0) + 1
    return out


def _er_relation_lines(domain: str, er: dict) -> list[str]:
    rels = [r for r in er.get("relationships") or []]
    if not rels:
        return []
    rels = sorted(rels, key=lambda x: (str(x.get("left")),
                                       str(x.get("right"))))
    # 圖形版（md 檢視器直接渲染）＋表格版（純文字也讀得懂）
    lines = [f"**`{domain}` 的實體關係**", "", "```mermaid", "erDiagram"]
    for r in rels:
        label = r.get("label") or '""'
        lines.append(f"    {r.get('left', '')} "
                     f"{r.get('left_cardinality', '--')}--"
                     f"{r.get('right_cardinality', '--')} "
                     f"{r.get('right', '')} : {label}")
    lines += ["```", "",
              "| from | 關係（基數記號） | to | 語意 |", "|---|---|---|---|"]
    for r in rels:
        left_c = str(r.get("left_cardinality", "")).replace("|", "\\|")
        right_c = str(r.get("right_cardinality", "")).replace("|", "\\|")
        lines.append(f"| `{r.get('left', '')}` | `{left_c}--{right_c}` "
                     f"| `{r.get('right', '')}` | {r.get('label', '')} |")
    lines.append("")
    return lines


def generate(config_dir: str = CONFIG_DIR) -> str:
    domains = _domains(config_dir)
    non_common = [d for d in domains if d != "Common"]
    entries = design_mod.design_index(config_dir, non_common)
    products = design_mod.load_products(config_dir, non_common)
    compiled_path, _ = ensure_compiled(
        config_dir, os.path.join(config_dir, "Common", "knowhow_py"),
        os.path.join(HERE, "build", "compiled_rules.json"))
    rules = _rule_counts(compiled_path)

    lines = [
        "# config 知識庫總索引（自動產生）", "",
        "> 重新產生：`python config_index.py`——新增或修改 config 文件後"
        "隨時重跑；內容確定性，config 沒變重跑結果相同。", "",
        "規則逐條明細另見 `docs/規則索引.generated.md`（由 "
        "`python rules.py check` 產生）。", "",
        "## 1. 網域（Product Suite）總覽", "",
        "| 網域 | ER 實體 | 詞彙字典 | SSOT 權威 | 產品 | 閘門規則 | 顧問規則 |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in domains:
        er = load_domain_er_full(config_dir, [] if d == "Common" else [d])
        if d != "Common":   # load_domain_er_full 恆含 Common，扣掉基底
            base = load_domain_er_full(config_dir, [])
            ents = sorted(set(er.get("entities") or {})
                          - set(base.get("entities") or {}))
        else:
            ents = sorted(er.get("entities") or {})
        ssot = _ssot(config_dir, d)
        registry = sorted((ssot.get("registry") or {}))
        codes = sorted(k for k, v in products["codes"].items()
                       if v.get("domain") == d)
        rc = rules.get(d, {})
        lines.append(
            f"| **{d}** | {'、'.join(f'`{e}`' for e in ents) or '—'} "
            f"| {'—' if not os.path.isdir(os.path.join(config_dir, d, 'naming')) else '有'} "
            f"| {'、'.join(f'`{e}`' for e in registry) or '—'} "
            f"| {'、'.join(f'`{c}`' for c in codes) or '—'} "
            f"| {rc.get('gating', 0)} | {rc.get('advisory', 0)} |")

    lines += ["", "## 2. 素材清單（全部檔案；🤖＝自動摘要待人工確認）", "",
              "| 素材 | 路徑 | 摘要 | 階段 | 必讀 | 狀態 |",
              "|---|---|---|---|---|---|"]
    for e in entries:
        lines.append(
            f"| {e['kind']} | `{e['path']}` | {e['summary']} "
            f"| {','.join(e['stage'])} | {'✅' if e['required'] else '—'} "
            f"| {'🤖' if e['auto_summary'] else '✍️'} |")

    lines += ["", "## 3. 關聯性", "",
              "### 3.1 各域 ER 參考模型（實體 × 關係）", ""]
    any_rel = False
    for d in domains:
        er = load_domain_er_full(config_dir,
                                 [d] if d != "Common" else [])
        rel_lines = _er_relation_lines(d, er)
        if d != "Common" and rel_lines:
            # 扣除 Common 基底的重複列示：Common 關係只在 Common 段列
            base_keys = {(str(r.get("left")), str(r.get("right")),
                          str(r.get("label")))
                         for r in load_domain_er_full(config_dir, [])
                         .get("relationships") or []}
            er = {"relationships": [
                r for r in er.get("relationships") or []
                if (str(r.get("left")), str(r.get("right")),
                    str(r.get("label"))) not in base_keys]}
            rel_lines = _er_relation_lines(d, er)
        if rel_lines:
            any_rel = True
            lines += rel_lines
    if not any_rel:
        lines += ["（各域 erd 尚無關係宣告）", ""]

    lines += ["### 3.2 SSOT 權威對照（同一事實誰是唯一權威）", "",
              "| 網域 | 實體 | 權威表 | 鍵 |", "|---|---|---|---|"]
    any_ssot = False
    for d in domains:
        for entity, spec in sorted((_ssot(config_dir, d).get("registry")
                                    or {}).items()):
            any_ssot = True
            spec = spec or {}
            lines.append(f"| {d} | `{entity}` "
                         f"| `{spec.get('authoritative_table', '')}` "
                         f"| `{spec.get('key', '')}` |")
    if not any_ssot:
        lines.append("| — | — | — | — |")

    lines += [
        "", "### 3.3 知識如何互相支撐（機制關聯）", "",
        "```mermaid",
        "flowchart LR",
        "  CTX[\"context.md<br/>domains / product\"] --> K[\"載入網域知識"
        "<br/>（Common 恆載入）\"]",
        "  K --> ERD[\"erd/ 參考模型<br/>＋表用途\"]",
        "  K --> NAM[\"naming/ 詞彙字典\"]",
        "  K --> SSOT[\"ssot/ 權威登錄\"]",
        "  K --> FLW[\"flows/ E2E 流程\"]",
        "  K --> PRD[\"products/ 產品縮寫\"]",
        "  K --> KH[\"knowhow/ 規則\"]",
        "  ERD --> P1[\"建議 DDL 對比<br/>（govern）\"]",
        "  ERD --> D1[\"design 實體依據\"]",
        "  NAM --> G1[\"naming_glossary 閘門\"]",
        "  NAM --> D2[\"design 命名決策順序\"]",
        "  SSOT --> G2[\"ssot_* 跨表閘門\"]",
        "  SSOT --> D3[\"design 領域邊界\"]",
        "  FLW --> D4[\"design 業務脈絡\"]",
        "  PRD --> D5[\"表名前綴規則＋逐表檢查\"]",
        "  KH --> G3[\"閘門（gating）\"]",
        "  KH --> A1[\"顧問（advisory）＋design know-how\"]",
        "```", "",
        "- `context.md` 的 `domains` 決定載入哪些網域知識（Common 恆載入）、"
        "`product` 決定表名前綴",
        "- `erd/`（參考模型）→ 建議 DDL 組建、design 起草的實體依據；"
        "`erd/tables/` → 表用途對照（ERD.TABLE_PURPOSE）",
        "- `naming/`（詞彙字典）→ `naming_glossary` 閘門實檢＋design 命名"
        "決策順序第 1 級",
        "- `ssot/`（權威登錄）→ `ssot_*` 跨表閘門規則＋design 領域邊界依據",
        "- `flows/`（E2E 流程）→ design 業務脈絡素材",
        "- `products/`（產品縮寫）→ 表名 `<分層>_<縮寫>_` 前綴規則與逐表檢查",
        "- `knowhow/`（規則）→ 閘門（gating）與顧問（advisory）；design "
        "以「設計約束」「設計 know-how」緊湊清單參照", "",
        "## 4. 標記（Tag）一覽", "",
        "| 標記 | 出現在 | 意義 |", "|---|---|---|",
        "| `L` | 素材索引「階段」 | logical 起草（業務世界）時要讀 |",
        "| `P` | 素材索引「階段」 | physical／DDL 落地時才要讀 |",
        "| `✅ 必讀` | 素材索引 | 設計必須讀並列入 narrative.references，"
        "漏了 design_story 會提醒 |",
        "| `🤖` | 索引狀態 | 摘要為自動萃取，待人工以 front-matter 確認 |",
        "| `✍️` | 索引狀態 | 已人工維護（檔案 front-matter 有 index_* 欄位）|",
        "| `index_summary / index_stage / index_required` | 素材檔 "
        "front-matter | 索引三欄位（皆選填），維護方式見 "
        "reports/design_index_review.md 表頭 |",
        "| `blocking / warning` | 閘門規則 enforcement | 會擋／只警告 |",
        "| `gating / advisory` | 規則 zone | 閘門（確定性、影響判定）／"
        "顧問（建議、永不影響判定）|",
        "| `base / intermediate / wide` | 設計積木層級 | 小積木（源頭表）／"
        "中積木（組合表）／寬表 |",
        "| " + "、".join(f"`{k}`" for k in (products["layers"] or
                                            {"ods": 0, "dim": 0, "dwd": 0,
                                             "dws": 0, "ads": 0}))
        + " | 表名分層前綴 | "
        + "；".join(f"{k}＝{v}" for k, v in (products["layers"] or {}).items())
        + " |",
        "",
    ]
    return "\n".join(lines)


def main():
    text = generate()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    old = None
    if os.path.isfile(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已更新總索引 → {os.path.relpath(OUT_PATH, HERE)}")
    else:
        print(f"總索引無變化 → {os.path.relpath(OUT_PATH, HERE)}")


if __name__ == "__main__":
    main()
