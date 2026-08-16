#!/usr/bin/env python3
"""design mode 的 HTML 報告——與 govern 報告（report.to_html）是兩份不同的東西。

視覺與定位刻意區隔：
  🎨 設計報告＝草稿演進（紫色系、無合規判定、純 <details> 摺疊、無 JS）
  🛡 治理報告＝合規判定（<名>.report.html，閘門結果、可篩選明細）

內容分門別類、階段清楚分開：
  敘事（給人讀）→ 🧠 Logical 階段（業務世界、六節）→
  🏗 Physical 階段（落地世界、DDL）→ 設計問答 → 產出檔案 →
  🗺 素材足跡 mindmap（全貌都畫出來；本輪實際讀過的檔案沿路徑標亮）

「實際讀過」的依據＝design_result 的 narrative.references（agent 宣告的
出處）；標必讀卻沒宣告的素材會在足跡上以 ⚠️ 顯示。輸出確定性（無時間戳）。
"""
from __future__ import annotations

import html as _html_mod

from .design import (LAYER_LABEL, all_relations, cross_table_checks,
                     downstream_edges, product_prefix_check,
                     question_id, question_text)
from .report import _origin_html


def _esc(s) -> str:
    return _html_mod.escape(str(s if s is not None else ""))


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """簡單表：cells 由呼叫端先處理跳脫（允許帶已組好的 HTML）。"""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                   for r in rows)
    return (f'<table><thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table>')


def _src_link(path: str) -> str:
    """config 路徑 → 可點連結（報告在 reports/，用 ../ 直達實際檔案）。"""
    return (f'<a class="src-link" target="_blank" rel="noopener" '
            f'href="../{_esc(path)}">{_esc(path)}</a>')


# ── 敘事（給人讀）────────────────────────────────────────────────────

def _story_html(result: dict) -> str:
    n = result.get("narrative") or {}
    parts = [f'<div class="tldr">{_esc(n.get("tldr", ""))}</div>',
             f'<h3>為什麼需要這個主體</h3><p>{_esc(n.get("why", ""))}</p>']
    if str(n.get("how_design_thinks", "")).strip():
        parts.append(f'<h3>設計是怎麼想的</h3>'
                     f'<p>{_esc(n["how_design_thinks"])}</p>')
    trs = n.get("tradeoffs") or []
    if trs:
        parts.append("<h3>關鍵取捨</h3><ul>")
        for t in trs:
            parts.append(
                f'<li><b>選擇</b>：{_esc(t.get("chose", ""))}'
                + (f'　<b>而不是</b>：{_esc(t.get("instead_of", ""))}'
                   if t.get("instead_of") else "")
                + f'<br><span class="muted">因為：'
                  f'{_esc(t.get("because", ""))}</span></li>')
        parts.append("</ul>")
    uses = n.get("how_to_use") or []
    if uses:
        parts.append("<h3>怎麼使用</h3><ul>")
        parts += [f'<li><b>{_esc(u.get("scenario", ""))}</b>：'
                  f'{_esc(u.get("guidance", ""))}</li>' for u in uses]
        parts.append("</ul>")
    if n.get("pitfalls"):
        parts.append("<h3>常見誤用與陷阱</h3><ul>")
        parts += [f'<li>⚠️ {_esc(p)}</li>' for p in n["pitfalls"]]
        parts.append("</ul>")
    if n.get("lessons"):
        parts.append("<h3>給工程師的啟發</h3><ul>")
        parts += [f'<li>💡 {_esc(x)}</li>' for x in n["lessons"]]
        parts.append("</ul>")
    refs = n.get("references") or []
    if refs:
        parts.append("<h3>設計出處（想法 → 來源）</h3><ul>")
        parts += [f'<li>{_src_link(str(r.get("source", "")))}：'
                  f'{_esc(r.get("how", ""))}</li>' for r in refs]
        parts.append("</ul>")
    return "".join(parts)


# ── 🧠 Logical 階段 ──────────────────────────────────────────────────

def _logical_html(result: dict) -> str:
    logical = result.get("logical_design") or {}
    parts = [f'<h3>1. Business Context（業務脈絡）</h3>'
             f'<p>{_esc(logical.get("business_context", "")) or "（無）"}</p>']
    boundary = logical.get("domain_boundary") or {}
    parts.append("<h3>2. Domain Boundary（領域邊界）</h3>"
                 f'<p>{_esc(boundary.get("statement", "")) or "（無）"}</p>')
    if boundary.get("owns"):
        parts.append('<p><b>本主體擁有的權威事實</b>：'
                     + "、".join(f"<code>{_esc(x)}</code>"
                                 for x in boundary["owns"]) + "</p>")
    brefs = boundary.get("references") or []
    if brefs:
        parts.append(_table(
            ["引用的外部實體", "權威位置", "備註"],
            [[f'<code>{_esc(r.get("entity", ""))}</code>',
              _esc(r.get("authority", "")), _esc(r.get("note", ""))]
             for r in brefs]))
    entities = logical.get("entities") or []
    parts.append("<h3>3. Entity Overview（實體總覽）</h3>")
    parts.append(_table(
        ["實體", "類型", "粒度", "Business Key", "說明"],
        [[f'<code>{_esc(e.get("name", "?"))}</code>', _esc(e.get("kind", "")),
          _esc(e.get("grain", "")),
          "、".join(f'<code>{_esc(a.get("name", ""))}</code>'
                    for a in (e.get("attributes") or [])
                    if a.get("business_key")),
          _esc(e.get("description", ""))] for e in entities]))
    rels = logical.get("relationships") or []
    if rels:
        parts.append("<p><b>實體關係</b></p>")
        parts.append(_table(
            ["from", "to", "基數", "說明"],
            [[f'<code>{_esc(r.get("from", ""))}</code>',
              f'<code>{_esc(r.get("to", ""))}</code>',
              _esc(r.get("cardinality", "")), _esc(r.get("description", ""))]
             for r in rels]))
    parts.append("<h3>4. Entity Detail（實體明細）</h3>")
    for e in entities:
        attrs = e.get("attributes") or []
        body = (f'<p>{_esc(e.get("description", ""))}'
                + (f'<br><b>粒度</b>：{_esc(e["grain"])}'
                   if e.get("grain") else "") + "</p>")
        if attrs:
            body += _table(
                ["屬性", "說明", "Business Key"],
                [[f'<code>{_esc(a.get("name", ""))}</code>',
                  _esc(a.get("description", "")),
                  "✅" if a.get("business_key") else ""] for a in attrs])
        parts.append(f'<details open><summary><code>'
                     f'{_esc(e.get("name", "?"))}</code>'
                     + (f'（{_esc(e.get("kind"))}）' if e.get("kind") else "")
                     + f'</summary>{body}</details>')
    contracts = logical.get("metric_contracts") or []
    parts.append("<h3>5. Metric Contracts（指標契約）</h3>")
    parts.append(_table(
        ["指標", "定義口徑", "粒度", "來源", "注意事項"],
        [[f'<b>{_esc(m.get("name", ""))}</b>', _esc(m.get("definition", "")),
          _esc(m.get("grain", "")), _esc(m.get("source", "")),
          _esc(m.get("caveats", ""))] for m in contracts])
        if contracts else "<p>（本主體未對下游承諾指標）</p>")
    deps = logical.get("cross_domain_dependencies") or []
    parts.append("<h3>6. Cross Domain Dependency（跨域依賴）</h3>")
    parts.append(_table(
        ["Domain", "實體", "方向", "介接鍵", "說明"],
        [[f'<code>{_esc(d.get("domain", ""))}</code>',
          f'<code>{_esc(d.get("entity", ""))}</code>',
          _esc(d.get("direction", "")),
          f'<code>{_esc(d.get("via", ""))}</code>',
          _esc(d.get("description", ""))] for d in deps])
        if deps else "<p>（無跨域依賴）</p>")
    # 7. Column Mapping（與 _logical_md 同一確定性規則）
    mapping = []
    for t in (result.get("physical_design") or {}).get("tables") or []:
        for c in t.get("columns") or []:
            src = str(c.get("source", "")).strip()
            if not src:
                continue
            new_name = str(c.get("name", ""))
            if src.lower().startswith("expression"):
                mark = "🧮 運算欄"
            else:
                last = src.split(".")[-1].strip()
                mark = ("✏️ 改名" if last and last.lower() != new_name.lower()
                        else "—")
            mapping.append([f"<code>{_esc(src)}</code>",
                            f'<code>{_esc(t.get("name", ""))}.'
                            f'{_esc(new_name)}</code>',
                            mark, _esc(c.get("comment", ""))])
    parts.append("<h3>7. Column Mapping（欄位來源對應）</h3>")
    parts.append(
        '<p class="muted">✏️＝已改名（欄名可比來源更有意義）；🧮＝運算欄。</p>'
        + _table(["來源（source）", "本設計欄位", "改名", "說明"], mapping)
        if mapping else "<p>（沒有宣告 source 的欄位——全部為本設計源生）</p>")
    return "".join(parts)


# ── 🏗 Physical 階段 ─────────────────────────────────────────────────

def _physical_html(name: str, result: dict, gate_preview: dict | None,
                   product: dict | None, ddl_diff: str) -> str:
    physical = result.get("physical_design") or {}
    tables = physical.get("tables") or []
    parts = []
    if str(physical.get("overview", "")).strip():
        parts.append(f'<p><b>實作策略</b>：{_esc(physical["overview"])}</p>')
    parts.append("<h3>1. Entity Overview（實體總覽）</h3>")
    parts.append(_table(
        ["表", "積木層級", "Business Key", "ENGINE", "ORDER BY",
         "PARTITION BY", "用途"],
        [[f'<code>{_esc(t.get("name", "?"))}</code>',
          _esc(LAYER_LABEL.get(t.get("layer"), t.get("layer") or "—")),
          "、".join(f"<code>{_esc(x)}</code>" for x in
                    (t.get("keys") or {}).get("business_key") or []) or "—",
          f'<code>{_esc(t.get("engine", ""))}</code>',
          f'<code>{_esc(t.get("order_by", ""))}</code>',
          f'<code>{_esc(t.get("partition_by", "") or "—")}</code>',
          _esc(t.get("comment", ""))] for t in tables]))
    rels = all_relations(result)
    parts.append("<h3>表間關係（Relations）</h3>")
    if rels:
        parts.append(_table(
            ["from（多的一方）", "to（一的一方）", "基數", "種類", "說明", "來源"],
            [[f'<code>{_esc(r.get("from", ""))}</code>',
              f'<code>{_esc(r.get("to", ""))}</code>',
              _esc(r.get("cardinality", "")), _esc(r.get("kind", "")),
              _esc(r.get("note", "")),
              "🔗 自動衍生" if r.get("origin") == "derived" else "宣告"]
             for r in rels]))
        parts.append(f'<p class="muted">relations 草稿已同步輸出：'
                     f'<code>{_esc(name)}.design.relations.yaml</code>'
                     f'——定稿時可直接沿用為 '
                     f'<code>input/{_esc(name)}/relations.yaml</code>。</p>')
    else:
        parts.append("<p>（未宣告且無外部 source——單表源生設計）</p>")
    edges = downstream_edges(tables)
    parts.append("<h3>2. Entity Detail（實體明細）</h3>")
    for t in tables:
        layer = LAYER_LABEL.get(t.get("layer"), t.get("layer") or "")
        keys = t.get("keys") or {}
        body = [f'<p>{_esc(t.get("comment", ""))}<br>'
                f'ENGINE <code>{_esc(t.get("engine", ""))}</code>'
                + (f' · ORDER BY <code>{_esc(t.get("order_by", ""))}</code>'
                   if t.get("order_by") else "")
                + (f' · PARTITION BY <code>'
                   f'{_esc(t.get("partition_by", ""))}</code>'
                   if t.get("partition_by") else "") + "</p>"]
        cols = t.get("columns") or []
        if cols:
            body.append(_table(
                ["欄位", "型別", "Nullable", "來源（從何處來）", "COMMENT"],
                [[f'<code>{_esc(c.get("name", ""))}</code>',
                  f'<code>{_esc(c.get("type", ""))}</code>',
                  "✅" if c.get("nullable") else "",
                  _esc(c.get("source", "") or "（本表源生）"),
                  _esc(c.get("comment", ""))] for c in cols]))
        body.append("<p><b>Key 設計</b></p><ul>")
        bk = keys.get("business_key") or []
        body.append("<li><b>Business Key</b>："
                    + ("、".join(f"<code>{_esc(x)}</code>" for x in bk)
                       if bk else "（未宣告）") + "</li>")
        if str(keys.get("description", "")).strip():
            body.append(f'<li><b>Key 語意</b>：'
                        f'{_esc(keys["description"])}</li>')
        for jk in keys.get("join_keys") or []:
            body.append(f'<li><b>Join Key</b>：'
                        f'<code>{_esc(jk.get("column", ""))}</code>'
                        + (f' → <code>{_esc(jk.get("references", ""))}</code>'
                           if jk.get("references") else "")
                        + (f'（{_esc(jk.get("note", ""))}）'
                           if jk.get("note") else "") + "</li>")
        body.append("</ul>")
        used_by = edges.get(str(t.get("name", ""))) or []
        body.append("<p><b>欄位去向</b>（由各表 source 確定性反推）</p><ul>"
                    + ("".join(f"<li>{_esc(e)}</li>" for e in used_by)
                       or "<li>（無下游設計表使用本表欄位）</li>") + "</ul>")
        decisions = t.get("design_decisions") or []
        if decisions:
            body.append("<p><b>設計決策與理由</b></p>")
            body.append(_table(["決策", "理由"],
                               [[_esc(d.get("decision", "")),
                                 _esc(d.get("rationale", ""))]
                                for d in decisions]))
        if str(t.get("ddl", "")).strip():
            body.append(f'<details><summary>DDL（草稿）</summary>'
                        f'<pre>{_esc(t["ddl"])}</pre></details>')
        parts.append(f'<details open><summary><code>'
                     f'{_esc(t.get("name", "?"))}</code>'
                     + (f' — {_esc(layer)}' if layer else "")
                     + f'</summary>{"".join(body)}</details>')
    prefix_rows = product_prefix_check(result, product)
    if prefix_rows:
        parts.append(f'<h3>表名產品前綴檢查（產品：'
                     f'<code>{_esc(product["code"])}</code>'
                     + (f'，{_esc(product.get("name", ""))}'
                        if product.get("name") else "") + "）</h3><ul>")
        parts += [f'<li>{"✅" if r["ok"] else "❌"} '
                  f'<code>{_esc(r["table"])}</code>'
                  + ("" if r["ok"]
                     else f' — 應為 <code>{_esc(r["expected"])}</code>')
                  + "</li>" for r in prefix_rows]
        parts.append("</ul>")
    xchecks = cross_table_checks(result)
    if xchecks:
        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
        parts.append("<h3>跨表比對（設計內多表一致性——確定性檢查）</h3><ul>")
        parts += [f'<li>{icon.get(x["status"], "")} <b>{_esc(x["check"])}</b>'
                  f'：{_esc(x["detail"])}</li>' for x in xchecks]
        parts.append("</ul>")
    parts.append("<h3>閘門預檢（以目前規則試跑草稿 DDL；設計參考、"
                 "非正式判定）</h3>")
    if not gate_preview:
        parts.append("<p>（本輪未執行預檢）</p>")
    elif gate_preview.get("parse_error"):
        parts.append(f'<p>❌ 草稿 DDL 無法解析：'
                     f'{_esc(gate_preview["parse_error"])}</p>')
    else:
        ok = gate_preview.get("compliant")
        parts.append(f'<p><span class="pchip {"ok" if ok else "bad"}">'
                     f'{"✅ 預檢合規" if ok else "❌ 預檢不合規"}</span>'
                     f'　fail {gate_preview.get("fail", 0)}、'
                     f'warning {gate_preview.get("warning", 0)}</p>')
        origins = gate_preview.get("origins") or {}

        def rule_li(icon: str, rule: str) -> str:
            origin = origins.get(rule)
            return (f'<li>{icon} <code>{_esc(rule)}</code>'
                    + (f' — 依據：{_origin_html(origin)}' if origin else "")
                    + "</li>")

        if gate_preview.get("blocked"):
            parts.append("<p><b>卡下來的規則</b>（點依據直達 config "
                         "規則檔）</p><ul>")
            parts += [rule_li("❌", r) for r in gate_preview["blocked"]]
            parts.append("</ul>")
        if gate_preview.get("warned"):
            parts.append("<p><b>警告的規則</b></p><ul>")
            parts += [rule_li("⚠️", r) for r in gate_preview["warned"]]
            parts.append("</ul>")
    notes = physical.get("notes") or []
    if notes:
        parts.append("<h3>設計注意事項</h3><ul>"
                     + "".join(f"<li>{_esc(x)}</li>" for x in notes) + "</ul>")
    if ddl_diff:
        parts.append(f'<details><summary>與上一輪設計的 DDL 演進（diff）'
                     f'</summary><pre class="diff">{_esc(ddl_diff)}</pre>'
                     f'</details>')
    return "".join(parts)


# ── 設計問答 ─────────────────────────────────────────────────────────

def _qa_html(name: str, result: dict, answers: dict | None) -> str:
    oq = result.get("open_questions") or []
    if not oq:
        return "<p>（無）</p>"
    by_id = {str(e.get("id", "")): e
             for e in (answers or {}).get("answers") or []
             if isinstance(e, dict)}
    label = {"proposed": '<span class="qchip q-p">⏳ 待驗證</span>',
             "answered": '<span class="qchip q-a">✅ 已答</span>',
             "deferred": '<span class="qchip q-d">⏸ 擱置</span>'}
    items = []
    for q in oq:
        text = question_text(q).strip()
        entry = by_id.get(question_id(text))
        status = str(entry.get("status", "proposed")) if entry else "proposed"
        items.append(
            f'<li>{label.get(status, _esc(status))} {_esc(text)}'
            + (f'<br><span class="muted">答案：'
               f'{_esc(entry.get("answer", ""))}</span>'
               if entry and status == "answered" else "") + "</li>")
    return (f'<p class="muted">驗證：<code>input/{_esc(name)}/'
            'design_answers.yaml</code> 把 proposed 改 answered／deferred。'
            "</p><ul>" + "".join(items) + "</ul>")


# ── 🗺 素材足跡 mindmap ──────────────────────────────────────────────

def _leaf(entry: dict, visited: set[str]) -> dict:
    on = entry["path"].lower() in visited
    miss = entry["required"] and not on
    return {"cls": "on" if on else "off", "miss": miss,
            "label": _src_link(entry["path"])
            + f' <span class="muted">{_esc(entry["summary"])}</span>'
            + (' <span class="miss">⚠️ 必讀未見於出處宣告</span>'
               if miss else "")}


def _branch(title: str, groups: dict[str, list[dict]]) -> dict:
    kids = []
    for kind, leaves in groups.items():
        kids.append({"cls": "on" if any(x["cls"] == "on" for x in leaves)
                     else "off", "label": _esc(kind), "children": leaves})
    total = sum(len(v) for v in groups.values())
    read = sum(1 for v in groups.values() for x in v if x["cls"] == "on")
    return {"cls": "on" if read else "off",
            "label": f"{_esc(title)}　<b>已讀 {read}／{total}</b>",
            "children": kids}


def _node_html(n: dict) -> str:
    dot = {"on": "●", "off": "○", "inline": "▣"}.get(n.get("cls", ""), "")
    kids = n.get("children") or []
    inner = (f'<ul class="mm">{"".join(_node_html(k) for k in kids)}</ul>'
             if kids else "")
    return (f'<li class="{n.get("cls", "")}">'
            f'<span class="nm">{dot} {n.get("label", "")}</span>{inner}</li>')


def footprint_html(name: str, round_no: int, domains: list[str],
                   product: dict | None, entries: list[dict],
                   refs: list[str]) -> str:
    """漸進式揭露足跡樹：全貌照畫（①緊湊層→②必讀→③L→④P），
    本輪實際讀過（narrative.references 宣告）的檔案沿路徑標亮。"""
    visited = {r.strip().lower() for r in refs if str(r).strip()}
    buckets: dict[str, dict[str, list[dict]]] = {"REQ": {}, "L": {}, "P": {}}
    for e in entries:
        keys = ["REQ"] if e["required"] else \
            [s for s in ("L", "P") if s in e["stage"]]
        for key in keys:
            buckets[key].setdefault(e["kind"], []).append(_leaf(e, visited))
    root_kids = [
        {"cls": "on", "label": f"起點：<code>input/{_esc(name)}/context.md"
         "</code>", "children": [
             {"cls": "on", "label": "domains："
              + ("、".join(f"<code>{_esc(d)}</code>" for d in domains)
                 or "（未宣告）") + "（Common 恆載）"},
             {"cls": "on" if product else "off",
              "label": "product："
              + (f'<code>{_esc(product["code"])}</code>（表名前綴）'
                 if product else "（未宣告）")}]},
        {"cls": "inline", "label": "① 內嵌緊湊層（隨 prompt 附上，不開檔）",
         "children": [{"cls": "inline", "label": _esc(x)} for x in (
             "設計約束（gating 摘要）", "設計 know-how（advisory 摘要）",
             "詞彙字典（合併一份）", "素材索引（每檔一行摘要）")]},
        _branch("② 必讀 ✅（一定開檔）", buckets["REQ"]),
        _branch("③ logical 起草才開（L）", buckets["L"]),
        _branch("④ physical 落地才開（P）", buckets["P"]),
    ]
    legend = ('<p class="muted">●＝本輪已讀（narrative.references 宣告的'
              '出處）；○＝未讀（僅載入索引摘要，省 context）；▣＝內嵌'
              '（緊湊層必附）。彩色連線＝實際走過的路徑。</p>')
    tree = (f'<div class="mm-root">🗺 一次設計執行 — {_esc(name)}'
            f'（第 {round_no} 輪）</div>'
            f'<ul class="mm">{"".join(_node_html(k) for k in root_kids)}</ul>')
    return legend + tree


# ── 組裝 ─────────────────────────────────────────────────────────────

def to_html(name: str, round_no: int, result: dict, *,
            state: str = "", gate_preview: dict | None = None,
            answers: dict | None = None, entries: list[dict] | None = None,
            product: dict | None = None, domains: list[str] | None = None,
            ddl_diff: str = "", files: list[str] | None = None) -> str:
    """設計報告 HTML（確定性、無時間戳、無 JS——與 govern 報告明顯不同）。"""
    n = result.get("narrative") or {}
    refs = [str(r.get("source", ""))
            for r in n.get("references") or [] if isinstance(r, dict)]
    preview_chip = ""
    if gate_preview and "compliant" in gate_preview:
        ok = gate_preview.get("compliant")
        preview_chip = (f'<span class="pchip {"ok" if ok else "bad"}">'
                        f'{"✅ 預檢合規" if ok else "❌ 預檢不合規"}'
                        "（參考）</span>")
    elif gate_preview and gate_preview.get("parse_error"):
        preview_chip = '<span class="pchip bad">預檢略過（DDL 解析失敗）</span>'
    files_html = ""
    if files:
        files_html = ("<ul>" + "".join(
            f'<li><a class="src-link" href="{_esc(f)}"><code>{_esc(f)}</code>'
            "</a></li>" for f in files) + "</ul>")
    tables = (result.get("physical_design") or {}).get("tables") or []
    ddl_dir_note = (f'<p class="muted">逐表 DDL 拆檔（積木）：'
                    f'<code>{_esc(name)}.design/</code>（{len(tables)} 份）'
                    "</p>" if any(str(t.get("ddl", "")).strip()
                                  for t in tables) else "")
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🎨 設計報告 — {_esc(name)}（第 {round_no} 輪）</title>
<style>
  :root {{
    --bg:#faf9fc; --card:#fff; --ink:#231c33; --muted:#6f6a7d; --line:#e6e2ef;
    --accent:#7c3aed; --accent-bg:#f3eefe;
    --l:#0284c7; --l-bg:#e0f2fe; --p:#d97706; --p-bg:#fef3c7;
    --ok:#15803d; --ok-bg:#dcfce7; --bad:#b91c1c; --bad-bg:#fee2e2;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#141020; --card:#1d1730; --ink:#eae6f4; --muted:#a49dbb;
      --line:#332a4d; --accent-bg:#2a2145; --l-bg:#0c2e42; --p-bg:#3a2a10;
      --ok-bg:#123322; --bad-bg:#3a1515; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); line-height:1.65;
    font-family:-apple-system,"Segoe UI","Microsoft JhengHei",sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:24px 18px 64px; }}
  .dhead {{ background:linear-gradient(135deg,#6d28d9,#2563eb 70%,#0ea5e9);
    color:#fff; border-radius:16px; padding:20px 24px; margin-bottom:14px; }}
  .dhead h1 {{ margin:0 0 6px; font-size:22px; }}
  .dhead .sub {{ opacity:.92; font-size:13.5px; }}
  .modebar {{ display:flex; flex-wrap:wrap; gap:10px; margin:0 0 16px; }}
  .modebox {{ flex:1; min-width:280px; background:var(--card);
    border:1px solid var(--line); border-radius:10px; padding:10px 14px;
    font-size:13px; color:var(--muted); }}
  .modebox.this {{ border-left:4px solid var(--accent); }}
  .modebox.that {{ border-left:4px solid #64748b; }}
  section.blk {{ background:var(--card); border:1px solid var(--line);
    border-radius:14px; padding:16px 20px; margin:16px 0; }}
  section.stage-l {{ border-left:6px solid var(--l); }}
  section.stage-p {{ border-left:6px solid var(--p); }}
  section.blk > h2 {{ margin:0 0 10px; font-size:17px; display:flex;
    align-items:center; gap:10px; flex-wrap:wrap; }}
  .schip {{ font-size:12px; padding:2px 10px; border-radius:999px;
    color:#fff; font-weight:600; }}
  .schip.l {{ background:var(--l); }} .schip.p {{ background:var(--p); }}
  .schip.a {{ background:var(--accent); }}
  h3 {{ font-size:14.5px; margin:16px 0 6px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px;
    margin:6px 0 10px; }}
  th, td {{ text-align:left; padding:7px 10px; border-top:1px solid var(--line);
    vertical-align:top; overflow-wrap:anywhere; }}
  th {{ color:var(--muted); font-weight:500; font-size:12px; }}
  code {{ font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12.5px;
    background:var(--accent-bg); border-radius:4px; padding:0 4px; }}
  pre {{ background:var(--bg); border:1px solid var(--line); border-radius:8px;
    padding:10px 12px; font-size:12px; overflow-x:auto; }}
  .tldr {{ background:var(--accent-bg); border-left:4px solid var(--accent);
    border-radius:8px; padding:10px 14px; font-weight:600; }}
  .muted {{ color:var(--muted); font-size:12.5px; }}
  .src-link {{ color:var(--accent); text-decoration:none; }}
  .src-link:hover {{ text-decoration:underline; }}
  .pchip {{ font-size:12.5px; padding:2px 10px; border-radius:999px;
    font-weight:600; }}
  .pchip.ok {{ color:var(--ok); background:var(--ok-bg); }}
  .pchip.bad {{ color:var(--bad); background:var(--bad-bg); }}
  .qchip {{ font-size:12px; padding:1px 8px; border-radius:999px; }}
  .q-p {{ background:var(--p-bg); color:var(--p); }}
  .q-a {{ background:var(--ok-bg); color:var(--ok); }}
  .q-d {{ background:var(--line); color:var(--muted); }}
  details {{ border:1px solid var(--line); border-radius:10px;
    padding:8px 14px; margin:8px 0; }}
  details summary {{ cursor:pointer; font-weight:600; font-size:13.5px; }}
  .rndchip {{ background:rgba(255,255,255,.2); border-radius:999px;
    padding:2px 12px; font-size:13px; }}
  /* 素材足跡樹：彩色連線＝實際走過的路徑 */
  .mm-root {{ font-weight:700; font-size:15px; margin:8px 0 2px; }}
  ul.mm {{ list-style:none; margin:0; padding-left:18px; }}
  ul.mm li {{ position:relative; padding:2px 0 2px 16px; }}
  ul.mm li::before {{ content:""; position:absolute; left:0; top:0; bottom:0;
    border-left:2px solid var(--line); }}
  ul.mm li::after {{ content:""; position:absolute; left:0; top:14px;
    width:12px; border-top:2px solid var(--line); }}
  ul.mm li:last-child::before {{ bottom:auto; height:14px; }}
  ul.mm li.on::before, ul.mm li.on::after {{ border-color:var(--accent); }}
  ul.mm li.on > .nm {{ font-weight:600; }}
  ul.mm li.off > .nm {{ color:var(--muted); }}
  ul.mm li.inline > .nm {{ color:var(--muted); }}
  .miss {{ color:var(--bad); font-size:12px; font-weight:600; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="dhead">
    <h1>🎨 設計報告（design mode） — {_esc(name)}</h1>
    <div class="sub"><span class="rndchip">第 {round_no} 輪設計{
        f'（{_esc(state)}）' if state else ''}</span>　{preview_chip}
      　草稿會隨迭代演進；定稿與否由使用者決定。</div>
  </div>
  <div class="modebar">
    <div class="modebox this"><b>🎨 這份是設計報告</b>——敘事＋邏輯／實體設計
      ＋素材足跡；<b>不做合規判定</b>（閘門預檢僅供參考）。</div>
    <div class="modebox that"><b>🛡 治理報告是另一份</b>——定稿進 govern mode
      後產生 <code>{_esc(name)}.report.html</code>，那份才有正式閘門判定。</div>
  </div>

  <section class="blk">
    <h2><span class="schip a">敘事</span>設計故事（給人讀）</h2>
    {_story_html(result)}
  </section>

  <section class="blk stage-l">
    <h2><span class="schip l">階段 L</span>🧠 Logical 階段 — 業務世界（六節）</h2>
    {_logical_html(result)}
  </section>

  <section class="blk stage-p">
    <h2><span class="schip p">階段 P</span>🏗 Physical 階段 — 落地世界（DDL）</h2>
    {_physical_html(name, result, gate_preview, product, ddl_diff)}
  </section>

  <section class="blk">
    <h2><span class="schip a">問答</span>❓ 設計問答（迭代收斂）</h2>
    {_qa_html(name, result, answers)}
  </section>

  <section class="blk">
    <h2><span class="schip a">產出</span>📁 本輪產出檔案</h2>
    {files_html or "<p>（無）</p>"}{ddl_dir_note}
  </section>

  <section class="blk">
    <h2><span class="schip a">足跡</span>🗺 素材足跡（漸進式揭露——全貌與
      實際路徑）</h2>
    {footprint_html(name, round_no, domains or [], product,
                    entries or [], refs)}
  </section>
</div>
</body>
</html>"""
