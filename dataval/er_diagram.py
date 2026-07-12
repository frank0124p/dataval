"""Minimal Mermaid ER diagram parser used as lineage evidence.

ER relationships describe structural associations, not observed data flow.
The parser therefore returns evidence only; lineage.py decides whether a safe
direction can be suggested from Business Keys and shared identifier columns.
"""
from __future__ import annotations

import re


_ENTITY = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*$")
_COLUMN = re.compile(r"^\s*(\S+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*?)\s*$")
_RELATION = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"([|o}{]+)--([|o}{]+)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$")


def parse_mermaid(text: str, source: str = "") -> dict:
    """Parse the common ``erDiagram`` subset without external dependencies."""
    entities: dict[str, dict] = {}
    relationships: list[dict] = []
    errors: list[str] = []
    current: str | None = None
    saw_header = False

    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        if line in ("```mermaid", "```"):
            continue
        if line == "erDiagram":
            saw_header = True
            continue
        if current:
            if line == "}":
                current = None
                continue
            match = _COLUMN.match(raw)
            if not match:
                errors.append(f"第 {line_number} 行無法解析 entity 欄位：{line}")
                continue
            raw_type, name, rest = match.groups()
            flags = [flag for flag in ("PK", "FK", "UK")
                     if re.search(rf"\b{flag}\b", rest, re.IGNORECASE)]
            entities[current]["columns"].append({
                "name": name,
                "type": raw_type,
                "flags": flags,
            })
            continue

        entity = _ENTITY.match(raw)
        if entity:
            current = entity.group(1)
            entities.setdefault(current, {"name": current, "columns": []})
            continue
        relation = _RELATION.match(raw)
        if relation:
            left, left_cardinality, right_cardinality, right, label = relation.groups()
            relationships.append({
                "left": left,
                "right": right,
                "left_cardinality": left_cardinality,
                "right_cardinality": right_cardinality,
                "label": label,
            })
            entities.setdefault(left, {"name": left, "columns": []})
            entities.setdefault(right, {"name": right, "columns": []})
            continue
        errors.append(f"第 {line_number} 行無法解析：{line}")

    if current:
        errors.append(f"entity '{current}' 缺少結尾 }}")
    if not saw_header:
        errors.append("缺少 erDiagram 標頭")
    return {
        "source": source,
        "entities": entities,
        "relationships": relationships,
        "errors": errors,
    }
