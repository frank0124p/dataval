"""E2E 流程（domain flows）。

標準格式：config/<域>/flows/<流程名>.md——第一個 `# 標題` 是流程名稱，
```mermaid fence 內放 flowchart，節點名對得上本次 DDL 的表就是表站點：

    # 訂單到營收
    結帳服務寫入訂單,展開明細,匯總成營收報表。

    ```mermaid
    flowchart LR
      結帳服務 --> orders --> order_items --> 營收日報
    ```

支援分支圖：上下游以圖的前驅／後繼計算，不限一直線。
舊式 `*.flow.yaml`（stages + kind: source|table|report）仍相容。

引擎行為（確定性、只出資訊與診斷，不擋）：
  FLOW.CONTEXT（info／顧問區）  本次 DDL 的表出現在某流程時，標註它的
      位置與上下游站點——讓設計者與審查者知道這張表在端到端流程的角色。
  FLOW.SPEC（warning／閘門區）  flow 檔無法解析或缺必要欄位時提醒，
      不靜默吞掉。
"""
from __future__ import annotations

import os
import re

import yaml

from .er_diagram import extract_mermaid
from .model import Finding, Schema, ZONE_ADVISORY, ZONE_GATING

VALID_KINDS = ("source", "table", "report")

#: mermaid flowchart 的節點 token：id 後可接各種形狀的標籤。
_FLOW_NODE = re.compile(
    r"^(?P<id>[^\s\[\(\{]+)\s*"
    r"(?:\[\((?P<cyl>.*?)\)\]|\(\[(?P<stad>.*?)\]\)|\(\((?P<circ>.*?)\)\)|"
    r"\{\{(?P<hex>.*?)\}\}|\[(?P<rect>.*?)\]|\((?P<round>.*?)\))?\s*$")
_FLOW_ARROW = re.compile(r"\s*-->(?:\|[^|]*\|)?\s*")
_FLOW_SKIP = re.compile(
    r"^(classDef|class|style|linkStyle|click|subgraph|end$|direction)\b|^%%")


def _parse_flow_node(token: str) -> tuple[str, str] | None:
    """節點 token → (id, 顯示名)。顯示名取標籤，無標籤用 id。"""
    m = _FLOW_NODE.match(token.strip())
    if not m or not m.group("id"):
        return None
    label = next((g for g in (m.group("cyl"), m.group("stad"), m.group("circ"),
                              m.group("hex"), m.group("rect"), m.group("round"))
                  if g is not None), None)
    display = (label or m.group("id")).strip().strip('"').strip()
    return m.group("id"), display or m.group("id")


def parse_flow_md(text: str, name: str) -> dict:
    """Markdown（含 mermaid flowchart）→ flow spec。格式錯誤丟 ValueError。"""
    title_match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else name
    mermaid = extract_mermaid(text)
    if mermaid == text and "```" not in text:
        raise ValueError("缺 ```mermaid 區塊（flowchart 放在 fence 內）")
    lines = [ln.strip() for ln in mermaid.splitlines() if ln.strip()]
    if not lines or not re.match(r"^(flowchart|graph)\b", lines[0]):
        raise ValueError("mermaid 區塊缺 flowchart 標頭（如 flowchart LR）")
    nodes: dict[str, str] = {}      # id → 顯示名（保出現順序）
    edges: list[tuple[str, str]] = []
    for line in lines[1:]:
        if _FLOW_SKIP.match(line):
            continue
        parts = _FLOW_ARROW.split(line)
        parsed = [_parse_flow_node(p) for p in parts]
        if any(p is None for p in parsed):
            raise ValueError(f"無法解析節點：{line}")
        for node_id, display in parsed:
            if node_id not in nodes or display != node_id:
                nodes[node_id] = display
        for (a, _), (b, _) in zip(parsed, parsed[1:]):
            if (a, b) not in edges:
                edges.append((a, b))
    if not edges:
        raise ValueError("flowchart 沒有任何站點連線（A --> B）")
    return {"flow": name, "title": title, "_nodes": nodes, "_edges": edges,
            "_format": "md"}


def _domain_folders(config_dir: str, domains: list[str] | None) -> list[str]:
    root = config_dir
    if os.path.isdir(os.path.join(config_dir, "domains")):
        root = os.path.join(config_dir, "domains")  # 舊佈局相容
    if not os.path.isdir(root):
        return []
    folders = {f.lower(): f for f in os.listdir(root)
               if os.path.isdir(os.path.join(root, f))
               and not f.startswith("_")}
    out, seen = [], set()
    for want in ["Common"] + [d for d in (domains or []) if d]:
        folder = folders.get(want.strip().lower())
        if folder and folder not in seen:
            seen.add(folder)
            out.append(os.path.join(root, folder))
    return out


def load_flows(config_dir: str, domains: list[str] | None
               ) -> tuple[list[dict], list[Finding]]:
    """載入流程定義。回傳 (flows, 診斷 findings)。"""
    flows: list[dict] = []
    problems: list[Finding] = []
    for dom_path in _domain_folders(config_dir, domains):
        flows_dir = os.path.join(dom_path, "flows")
        if not os.path.isdir(flows_dir):
            continue
        domain = os.path.basename(dom_path)
        for fn in sorted(os.listdir(flows_dir)):
            path = os.path.join(flows_dir, fn)
            label = f"{domain}/flows/{fn}"
            # 標準格式：.md（含 mermaid flowchart）；README 跳過
            if fn.endswith(".md") and not fn.lower().startswith("readme"):
                try:
                    with open(path, encoding="utf-8") as f:
                        spec = parse_flow_md(f.read(), os.path.splitext(fn)[0])
                except Exception as e:
                    problems.append(Finding(
                        "FLOW.SPEC", "structural", "warning", label,
                        f"E2E 流程檔無法使用：{type(e).__name__}: {e}",
                        severity="warning", source="rule", zone=ZONE_GATING,
                        fix="Markdown 內放 ```mermaid flowchart（節點用 --> 相連）。"))
                    continue
                spec["_domain"], spec["_source"] = domain, label
                flows.append(spec)
                continue
            if not fn.endswith((".flow.yaml", ".flow.yml")):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    spec = yaml.safe_load(f) or {}
                if not isinstance(spec, dict):
                    raise ValueError("根節點必須是 mapping")
                stages = spec.get("stages")
                if not isinstance(stages, list) or not stages:
                    raise ValueError("缺 stages 清單")
                for i, stage in enumerate(stages, start=1):
                    if not isinstance(stage, dict) or not stage.get("name"):
                        raise ValueError(f"第 {i} 站缺 name")
                    kind = stage.get("kind", "table")
                    if kind not in VALID_KINDS:
                        raise ValueError(
                            f"第 {i} 站 kind '{kind}' 不合法"
                            f"（限 {'/'.join(VALID_KINDS)}）")
            except Exception as e:
                problems.append(Finding(
                    "FLOW.SPEC", "structural", "warning", label,
                    f"E2E 流程檔無法使用：{type(e).__name__}: {e}",
                    severity="warning", source="rule", zone=ZONE_GATING,
                    fix="依 flows 資料夾內範例的 YAML 格式修正。"))
                continue
            spec["_domain"], spec["_source"] = domain, label
            flows.append(spec)
    return flows, problems


def _md_flow_context(spec: dict, table_names: dict[str, str]) -> list[Finding]:
    """md flowchart：以圖的前驅／後繼標註表的上下游（支援分支）。"""
    out: list[Finding] = []
    nodes, edges = spec["_nodes"], spec["_edges"]
    title = spec.get("title") or spec.get("flow") or spec["_source"]
    for node_id, display in nodes.items():
        hit = (table_names.get(display.lower())
               or table_names.get(node_id.lower()))
        if not hit:
            continue
        prevs = [nodes[a] for a, b in edges if b == node_id]
        nexts = [nodes[b] for a, b in edges if a == node_id]
        prev_txt = "、".join(dict.fromkeys(prevs)) or "（起點）"
        next_txt = "、".join(dict.fromkeys(nexts)) or "（終點）"
        out.append(Finding(
            "FLOW.CONTEXT", "structural", "info", hit,
            f"此表位於 E2E 流程「{title}」（共 {len(nodes)} 站）；"
            f"上游站點：{prev_txt}；下游站點：{next_txt}。"
            f"設計變更時請沿流程確認上下游影響。（依據：config/{spec['_source']}）",
            severity="info", source="rule", zone=ZONE_ADVISORY))
    return out


def run(schema: Schema, domains: list[str] | None,
        config_dir: str) -> list[Finding]:
    flows, findings = load_flows(config_dir, domains)
    if not flows:
        return findings
    table_names = {t.name.lower(): t.name for t in schema.tables}
    for spec in flows:
        if spec.get("_format") == "md":
            findings.extend(_md_flow_context(spec, table_names))
            continue
        stages = spec["stages"]
        for idx, stage in enumerate(stages):
            if stage.get("kind", "table") != "table":
                continue
            hit = table_names.get(str(stage["name"]).lower())
            if not hit:
                continue
            prev_stage = stages[idx - 1]["name"] if idx > 0 else "（起點）"
            next_stage = (stages[idx + 1]["name"]
                          if idx + 1 < len(stages) else "（終點）")
            title = spec.get("title") or spec.get("flow") or spec["_source"]
            findings.append(Finding(
                "FLOW.CONTEXT", "structural", "info", hit,
                f"此表位於 E2E 流程「{title}」第 {idx + 1}/{len(stages)} 站；"
                f"上游站點：{prev_stage}；下游站點：{next_stage}。"
                f"設計變更時請沿流程確認上下游影響。（依據：config/{spec['_source']}）",
                severity="info", source="rule", zone=ZONE_ADVISORY))
    return findings
