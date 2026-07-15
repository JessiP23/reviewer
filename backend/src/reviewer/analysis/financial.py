from __future__ import annotations

import re
from dataclasses import dataclass

from reviewer.domain.models import Evidence, Finding, Metric, Severity
from reviewer.extraction.models import ExtractedBlock, ExtractedDocument

RULE_VERSION = "financial-core/1.0.0"


@dataclass(frozen=True)
class MetricPattern:
    key: str
    label: str
    pattern: re.Pattern[str]


METRIC_PATTERNS = (
    MetricPattern("revenue", "Revenue", re.compile(r"\b(?:total\s+)?(?:revenue|sales)\b", re.I)),
    MetricPattern(
        "cogs",
        "Cost of goods sold",
        re.compile(r"\b(?:cogs|cost of (?:goods sold|sales))\b", re.I),
    ),
    MetricPattern("gross_profit", "Gross profit", re.compile(r"\bgross profit\b", re.I)),
    MetricPattern(
        "operating_expenses",
        "Operating expenses",
        re.compile(r"\boperating expenses?\b", re.I),
    ),
    MetricPattern(
        "net_income",
        "Net income",
        re.compile(r"\b(?:net income|net profit|net earnings)\b", re.I),
    ),
    MetricPattern("cash", "Cash", re.compile(r"\b(?:cash(?: and cash equivalents)?)\b", re.I)),
    MetricPattern(
        "accounts_receivable",
        "Accounts receivable",
        re.compile(r"\baccounts receivable\b", re.I),
    ),
    MetricPattern("inventory", "Inventory", re.compile(r"\binventor(?:y|ies)\b", re.I)),
    MetricPattern(
        "current_assets", "Current assets", re.compile(r"\btotal current assets\b", re.I)
    ),
    MetricPattern("total_assets", "Total assets", re.compile(r"\btotal assets\b", re.I)),
    MetricPattern(
        "current_liabilities",
        "Current liabilities",
        re.compile(r"\btotal current liabilities\b", re.I),
    ),
    MetricPattern(
        "total_liabilities",
        "Total liabilities",
        re.compile(r"\btotal liabilities\b", re.I),
    ),
    MetricPattern(
        "equity",
        "Owners' equity",
        re.compile(r"\b(?:total )?(?:owners?'|shareholders?')?\s*equity\b", re.I),
    ),
    MetricPattern("debt", "Total debt", re.compile(r"\b(?:total debt|borrowings)\b", re.I)),
)

NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z])(?P<paren>\()?\s*(?P<currency>[$€£])?\s*"
    r"(?P<number>-?\d[\d,]*(?:\.\d+)?)\s*(?P<suffix>[kKmMbB])?\s*(?(paren)\))"
)


def _evidence(block: ExtractedBlock, text: str | None = None) -> Evidence:
    return Evidence(
        text=text or block.text[:500],
        source=block.source,
        page=block.page,
        sheet=block.sheet,
        cell_range=block.cell_range,
        start_offset=block.start_offset,
        end_offset=block.end_offset,
    )


def parse_number(raw: re.Match[str]) -> float:
    value = float(raw.group("number").replace(",", ""))
    suffix = (raw.group("suffix") or "").lower()
    value *= {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[suffix]
    if raw.group("paren") and value > 0:
        value *= -1
    return value


def extract_metrics(document: ExtractedDocument) -> list[Metric]:
    metrics: list[Metric] = []
    seen: set[str] = set()
    for block in document.blocks:
        for definition in METRIC_PATTERNS:
            if definition.key in seen or not definition.pattern.search(block.text):
                continue
            label_end = definition.pattern.search(block.text)
            assert label_end is not None
            candidates = list(NUMBER_PATTERN.finditer(block.text[label_end.end() :]))
            if not candidates:
                continue
            value = parse_number(candidates[-1])
            metrics.append(
                Metric(
                    key=definition.key,
                    label=definition.label,
                    value=value,
                    unit="currency",
                    confidence=0.96,
                    evidence=[_evidence(block)],
                )
            )
            seen.add(definition.key)
    return metrics


def _derived_metric(
    key: str,
    label: str,
    numerator: Metric,
    denominator: Metric,
    unit: str,
) -> Metric | None:
    if denominator.value == 0:
        return None
    factor = 100 if unit == "percent" else 1
    return Metric(
        key=key,
        label=label,
        value=(numerator.value / denominator.value) * factor,
        unit=unit,
        confidence=min(numerator.confidence, denominator.confidence),
        evidence=[*numerator.evidence, *denominator.evidence],
    )


def add_derived_metrics(metrics: list[Metric]) -> list[Metric]:
    by_key = {metric.key: metric for metric in metrics}
    derived: list[Metric] = []
    specifications = (
        ("gross_margin", "Gross margin", "gross_profit", "revenue", "percent"),
        ("net_margin", "Net margin", "net_income", "revenue", "percent"),
        ("current_ratio", "Current ratio", "current_assets", "current_liabilities", "ratio"),
        ("debt_to_equity", "Debt to equity", "debt", "equity", "ratio"),
    )
    for key, label, numerator_key, denominator_key, unit in specifications:
        if numerator_key in by_key and denominator_key in by_key:
            result = _derived_metric(
                key, label, by_key[numerator_key], by_key[denominator_key], unit
            )
            if result is not None:
                derived.append(result)
    return [*metrics, *derived]


def _finding(
    code: str,
    title: str,
    category: str,
    severity: Severity,
    explanation: str,
    recommendation: str,
    evidence: list[Evidence],
    confidence: float = 0.98,
    requires_human_review: bool = False,
) -> Finding:
    return Finding(
        code=code,
        title=title,
        category=category,
        severity=severity,
        explanation=explanation,
        recommendation=recommendation,
        confidence=confidence,
        evidence=evidence,
        requires_human_review=requires_human_review,
    )


def _numeric_rules(metrics: list[Metric]) -> list[Finding]:
    values = {metric.key: metric for metric in metrics}
    findings: list[Finding] = []

    if {"total_assets", "total_liabilities", "equity"} <= values.keys():
        assets = values["total_assets"]
        liabilities = values["total_liabilities"]
        equity = values["equity"]
        difference = assets.value - (liabilities.value + equity.value)
        tolerance = max(abs(assets.value) * 0.01, 1)
        if abs(difference) > tolerance:
            findings.append(
                _finding(
                    "BALANCE_SHEET_MISMATCH",
                    "Balance sheet does not balance",
                    "accounting-integrity",
                    Severity.CRITICAL,
                    f"Assets differ from liabilities plus equity by {difference:,.2f}.",
                    (
                        "Confirm periods, units, signs, and source cells before relying on "
                        "this statement."
                    ),
                    [*assets.evidence, *liabilities.evidence, *equity.evidence],
                    requires_human_review=True,
                )
            )

    if {"revenue", "cogs", "gross_profit"} <= values.keys():
        revenue, cogs, gross_profit = (
            values["revenue"],
            values["cogs"],
            values["gross_profit"],
        )
        difference = gross_profit.value - (revenue.value - cogs.value)
        tolerance = max(abs(revenue.value) * 0.01, 1)
        if abs(difference) > tolerance:
            findings.append(
                _finding(
                    "GROSS_PROFIT_MISMATCH",
                    "Gross profit is inconsistent",
                    "accounting-integrity",
                    Severity.HIGH,
                    f"Reported gross profit differs from revenue minus COGS by {difference:,.2f}.",
                    (
                        "Verify classification and source periods, then reconcile the "
                        "income statement."
                    ),
                    [*revenue.evidence, *cogs.evidence, *gross_profit.evidence],
                    requires_human_review=True,
                )
            )

    if "net_income" in values and values["net_income"].value < 0:
        metric = values["net_income"]
        findings.append(
            _finding(
                "NEGATIVE_NET_INCOME",
                "Business reports a net loss",
                "profitability",
                Severity.HIGH,
                f"Net income is {metric.value:,.2f} for the extracted period.",
                "Review expense drivers, one-time items, and cash runway with the business owner.",
                metric.evidence,
            )
        )

    if "current_ratio" in values and values["current_ratio"].value < 1:
        metric = values["current_ratio"]
        findings.append(
            _finding(
                "LOW_CURRENT_RATIO",
                "Short-term liquidity pressure",
                "liquidity",
                Severity.HIGH,
                f"Current ratio is {metric.value:.2f}, below the 1.00 screening threshold.",
                "Review timing of receivables, payables, inventory, and available credit.",
                metric.evidence,
                requires_human_review=True,
            )
        )

    if "debt_to_equity" in values and values["debt_to_equity"].value > 2:
        metric = values["debt_to_equity"]
        findings.append(
            _finding(
                "HIGH_DEBT_TO_EQUITY",
                "Elevated leverage indicator",
                "leverage",
                Severity.MEDIUM,
                (
                    f"Debt-to-equity is {metric.value:.2f}, above the generic 2.00 "
                    "screening threshold."
                ),
                "Compare leverage with industry peers and inspect debt pricing and covenants.",
                metric.evidence,
                confidence=0.9,
                requires_human_review=True,
            )
        )
    return findings


TEXT_RULES = (
    (
        "GOING_CONCERN_LANGUAGE",
        "Going-concern language detected",
        "solvency",
        Severity.CRITICAL,
        re.compile(r"\bsubstantial doubt.{0,120}\bgoing concern\b|\bgoing concern\b", re.I | re.S),
        "A source passage contains going-concern language.",
        "Escalate to a qualified accountant and review the complete audit note.",
    ),
    (
        "MATERIAL_WEAKNESS",
        "Material weakness disclosed",
        "controls",
        Severity.HIGH,
        re.compile(r"\bmaterial weakness(?:es)?\b", re.I),
        "A source passage mentions a material weakness in controls.",
        "Review the complete control deficiency, remediation status, and affected accounts.",
    ),
    (
        "PII_SSN",
        "Potential Social Security number",
        "data-protection",
        Severity.HIGH,
        re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
        "The document may contain sensitive personal data.",
        "Restrict access and redact the value before sharing or model processing.",
    ),
)


def _text_rules(document: ExtractedDocument) -> list[Finding]:
    findings: list[Finding] = []
    for block in document.blocks:
        for code, title, category, severity, pattern, explanation, recommendation in TEXT_RULES:
            match = pattern.search(block.text)
            if match is not None and not any(finding.code == code for finding in findings):
                start = max(match.start() - 90, 0)
                end = min(match.end() + 90, len(block.text))
                excerpt = block.text[start:end]
                if code == "PII_SSN":
                    excerpt = pattern.sub("***-**-****", excerpt)
                findings.append(
                    _finding(
                        code,
                        title,
                        category,
                        severity,
                        explanation,
                        recommendation,
                        [_evidence(block, excerpt)],
                        requires_human_review=True,
                    )
                )
    return findings


def analyze(document: ExtractedDocument) -> tuple[list[Metric], list[Finding]]:
    metrics = add_derived_metrics(extract_metrics(document))
    return metrics, [*_numeric_rules(metrics), *_text_rules(document)]
