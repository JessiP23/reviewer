from __future__ import annotations

# Backward-compatible re-exports from the schema-driven financial engine.
from reviewer.analysis.schema_engine import (
    NUMBER_PATTERN,
    RULE_VERSION,
    add_derived_metrics,
    analyze,
    extract_metrics,
    numeric_rules,
    parse_number,
)

__all__ = [
    "NUMBER_PATTERN",
    "RULE_VERSION",
    "add_derived_metrics",
    "analyze",
    "extract_metrics",
    "numeric_rules",
    "parse_number",
]
