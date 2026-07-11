"""Structured schema model + finding model for the two-zone architecture."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Column:
    name: str
    raw_type: str
    base_type: str
    nullable: bool = False
    is_pk: bool = False
    default: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class ForeignKey:
    columns: list[str]
    ref_table: str
    ref_columns: list[str]


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)  # explicit ClickHouse primary index
    sorting_key: list[str] = field(default_factory=list)  # ORDER BY / physical sorting key
    business_key: list[str] = field(default_factory=list) # stable business identifier
    business_key_source: str = ""                        # explicit | inferred_sorting_identifier
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    engine: Optional[str] = None
    comment: Optional[str] = None

    def col(self, name: str) -> Optional[Column]:
        return next((c for c in self.columns if c.name == name), None)


@dataclass
class Schema:
    tables: list[Table] = field(default_factory=list)
    dialect: str = "clickhouse"
    sample_data: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    context: str = ""

    def table(self, name: str) -> Optional[Table]:
        return next((t for t in self.tables if t.name == name), None)


SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}

# Two zones from the architecture:
ZONE_GATING = "gating"      # deterministic, can block
ZONE_ADVISORY = "advisory"  # LLM / judgement, info only, never blocks


@dataclass
class Finding:
    check_id: str
    category: str            # structural | naming | best_practice | ssot | datahub | concept
    status: str              # pass | fail | warning | info | skipped
    target: str
    message: str
    severity: str = "error"
    rationale: str = ""
    evidence: Any = None
    source: str = "rule"     # rule | skill | llm
    zone: str = ZONE_GATING  # gating | advisory
    expected: str = ""       # 規則要求什麼（四問之三：期望）
    actual: str = ""         # 實際看到什麼（四問之三：實際）
    fix: str = ""            # 怎麼修（四問之四）

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id, "category": self.category,
            "status": self.status, "target": self.target, "message": self.message,
            "severity": self.severity, "rationale": self.rationale,
            "evidence": self.evidence, "source": self.source, "zone": self.zone,
            "expected": self.expected, "actual": self.actual, "fix": self.fix,
        }
