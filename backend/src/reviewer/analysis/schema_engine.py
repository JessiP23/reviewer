from __future__ import annotations

import contextlib
import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

from reviewer.domain.models import Evidence, Finding, Metric, Severity
from reviewer.extraction.models import ExtractedBlock, ExtractedDocument

RULE_VERSION = "financial-schema/2.0.0"


@dataclass(frozen=True)
class AccountConcept:
    """Standard financial-account concept with many aliases.

    Aliases make the engine tolerant of wording differences across documents,
    jurisdictions, and statement formats without editing regex patterns.
    """

    key: str
    label: str
    category: str
    aliases: tuple[str, ...]
    # When True, a positive source value represents a negative economic amount
    # when the label contains loss/deficit language (e.g., "Net loss: $400k").
    is_contra: bool = False


CHART_OF_ACCOUNTS: dict[str, AccountConcept] = {
    "revenue": AccountConcept(
        "revenue",
        "Revenue",
        "income_statement",
        (
            "revenue",
            "total revenue",
            "sales",
            "total sales",
            "gross revenue",
            "turnover",
            "net sales",
            "operating revenue",
            "sales revenue",
        ),
    ),
    "cogs": AccountConcept(
        "cogs",
        "Cost of goods sold",
        "income_statement",
        (
            "cost of goods sold",
            "cost of sales",
            "cogs",
            "cost of revenue",
            "direct costs",
            "cost of materials",
        ),
    ),
    "gross_profit": AccountConcept(
        "gross_profit",
        "Gross profit",
        "income_statement",
        (
            "gross profit",
            "gross margin",
            "gross income",
        ),
    ),
    "operating_expenses": AccountConcept(
        "operating_expenses",
        "Operating expenses",
        "income_statement",
        (
            "operating expenses",
            "operating expense",
            "selling general and administrative",
            "sg&a",
            "selling, general and administrative",
            "overhead",
            "general and administrative",
            "administrative expenses",
        ),
    ),
    "operating_income": AccountConcept(
        "operating_income",
        "Operating income",
        "income_statement",
        (
            "operating income",
            "operating profit",
            "ebit",
            "earnings before interest and taxes",
            "income from operations",
        ),
    ),
    "ebitda": AccountConcept(
        "ebitda",
        "EBITDA",
        "income_statement",
        (
            "ebitda",
            "earnings before interest taxes depreciation and amortization",
        ),
    ),
    "interest_expense": AccountConcept(
        "interest_expense",
        "Interest expense",
        "income_statement",
        (
            "interest expense",
            "interest payable",
            "finance cost",
            "finance costs",
            "interest charges",
        ),
    ),
    "tax_expense": AccountConcept(
        "tax_expense",
        "Income tax expense",
        "income_statement",
        (
            "income tax expense",
            "tax expense",
            "taxes",
            "provision for income taxes",
            "income taxes",
        ),
    ),
    "depreciation": AccountConcept(
        "depreciation",
        "Depreciation and amortization",
        "income_statement",
        (
            "depreciation",
            "amortization",
            "depreciation and amortization",
            "d&a",
        ),
    ),
    "net_income": AccountConcept(
        "net_income",
        "Net income",
        "income_statement",
        (
            "net income",
            "net profit",
            "net earnings",
            "bottom line",
            "profit after tax",
            "profit for the period",
            "net loss",
            "loss for the period",
            "loss",
        ),
        is_contra=True,
    ),
    "cash": AccountConcept(
        "cash",
        "Cash and cash equivalents",
        "balance_sheet",
        (
            "cash",
            "cash and cash equivalents",
            "cash and equivalents",
            "cash at bank",
            "bank and cash",
            "cash and due from banks",
        ),
    ),
    "accounts_receivable": AccountConcept(
        "accounts_receivable",
        "Accounts receivable",
        "balance_sheet",
        (
            "accounts receivable",
            "trade receivables",
            "debtors",
            "receivables",
            "accounts and notes receivable",
        ),
    ),
    "inventory": AccountConcept(
        "inventory",
        "Inventory",
        "balance_sheet",
        (
            "inventory",
            "inventories",
            "stock",
            "merchandise inventory",
            "raw materials",
            "finished goods",
        ),
    ),
    "current_assets": AccountConcept(
        "current_assets",
        "Total current assets",
        "balance_sheet",
        (
            "total current assets",
            "current assets",
            "current assets total",
        ),
    ),
    "total_assets": AccountConcept(
        "total_assets",
        "Total assets",
        "balance_sheet",
        (
            "total assets",
            "assets total",
            "total of assets",
        ),
    ),
    "current_liabilities": AccountConcept(
        "current_liabilities",
        "Total current liabilities",
        "balance_sheet",
        (
            "total current liabilities",
            "current liabilities",
            "current liabilities total",
        ),
    ),
    "total_liabilities": AccountConcept(
        "total_liabilities",
        "Total liabilities",
        "balance_sheet",
        (
            "total liabilities",
            "liabilities total",
            "total of liabilities",
        ),
    ),
    "total_liabilities_and_equity": AccountConcept(
        "total_liabilities_and_equity",
        "Total liabilities and equity",
        "balance_sheet",
        (
            "total liabilities and equity",
            "total liabilities and shareholders equity",
            "total liabilities and stockholders equity",
            "total liabilities and owners equity",
            "total liabilities & equity",
        ),
    ),
    "equity": AccountConcept(
        "equity",
        "Owners' equity",
        "balance_sheet",
        (
            "total equity",
            "owners equity",
            "shareholders equity",
            "stockholders equity",
            "share capital",
            "total shareholders equity",
            "total stockholders equity",
            "total owners equity",
            "net assets",
            "shareholders funds",
        ),
    ),
    "debt": AccountConcept(
        "debt",
        "Total debt",
        "balance_sheet",
        (
            "total debt",
            "long-term debt",
            "short-term debt",
            "borrowings",
            "notes payable",
            "loans payable",
            "debt",
            "long term borrowings",
            "short term borrowings",
        ),
    ),
}


# Regex that tolerates currency symbols, thousand separators, suffixes, and
# parenthetical negatives with optional surrounding whitespace.
NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z])\s*(?P<paren>\()?\s*(?P<currency>[$€£¥])?\s*"
    r"(?P<number>-?\d[\d,]*(?:\.\d+)?)\s*(?P<suffix>[kKmMbBtT])?\s*(?(paren)\))"
)


LOSS_WORDS = re.compile(r"\b(loss|deficit|negative|net loss|loss for)\b", re.I)


@dataclass(frozen=True)
class ParsedValue:
    raw: str
    value: float
    confidence: float
    flags: tuple[str, ...]


@dataclass(frozen=True)
class ExtractedCell:
    label: str
    raw_value: str
    period: str | None
    account: AccountConcept | None
    match_score: float
    block: ExtractedBlock


def _normalize_label(text: str) -> str:
    """Lowercase, remove punctuation except &, collapse spaces."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s&]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _score_label_to_alias(label: str, alias: str) -> float:
    """Hybrid similarity: sequence ratio or token overlap, whichever is higher."""
    label_norm = _normalize_label(label)
    alias_norm = _normalize_label(alias)
    if not label_norm or not alias_norm:
        return 0.0
    seq = SequenceMatcher(None, label_norm, alias_norm).ratio()
    label_tokens = set(label_norm.split())
    alias_tokens = set(alias_norm.split())
    if not label_tokens or not alias_tokens:
        return seq
    overlap = len(label_tokens & alias_tokens) / max(len(label_tokens), len(alias_tokens))
    # Give a small bonus for exact prefix equality.
    prefix_bonus = (
        0.05 if label_norm.startswith(alias_norm) or alias_norm.startswith(label_norm) else 0.0
    )
    return max(seq, overlap) + prefix_bonus


def _match_account(label: str, threshold: float = 0.65) -> tuple[AccountConcept | None, float, str]:
    """Link a raw label to the best standard account concept."""
    if not label.strip():
        return None, 0.0, ""
    best_score = 0.0
    best_account: AccountConcept | None = None
    best_alias = ""
    for account in CHART_OF_ACCOUNTS.values():
        for alias in account.aliases:
            score = _score_label_to_alias(label, alias)
            if score > best_score:
                best_score = score
                best_account = account
                best_alias = alias
    if best_score < threshold:
        return None, best_score, best_alias
    return best_account, best_score, best_alias


def parse_number(raw: re.Match[str]) -> float:
    """Convert a NUMBER_PATTERN match into a normalized float.

    Parentheses and explicit minus signs both force a negative value.
    Suffix k/m/b/t scale the raw amount.
    """
    value = float(raw.group("number").replace(",", ""))
    suffix = (raw.group("suffix") or "").lower()
    value *= {
        "": 1,
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
        "t": 1_000_000_000_000,
    }[suffix]
    if raw.group("paren") is not None:
        value = -abs(value)
    return value


def _parse_value_token(token: str) -> ParsedValue | None:
    """Parse a single numeric string into a value, confidence, and risk flags."""
    match = NUMBER_PATTERN.search(token)
    if match is None:
        return None
    raw = match.group(0).strip()
    value = parse_number(match)
    flags: list[str] = []
    confidence = 1.0
    if match.group("paren") is not None:
        flags.append("parenthetical_negative")
        if value > 0:
            # Should never happen because parse_number forces negative, but flag if it does.
            flags.append("positive_in_parens")
    if match.group("suffix"):
        flags.append("scaled_by_suffix")
    if match.group("currency"):
        flags.append("currency_stripped")
    # Penalize European-format ambiguity (1.200 without suffix could be 1.2 thousand or 1200).
    number_part = match.group("number")
    if "." in number_part and len(number_part.split(".")[-1]) == 3 and not match.group("suffix"):
        flags.append("possible_european_thousands")
        confidence *= 0.85
    if flags:
        confidence *= 0.98 ** len(flags)
    return ParsedValue(raw=raw, value=value, confidence=round(confidence, 4), flags=tuple(flags))


def _detect_negative_from_label(label: str, value: float) -> tuple[float, list[str]]:
    """Infer whether a positive value should be negative based on label words."""
    flags: list[str] = []
    if LOSS_WORDS.search(label) and value > 0:
        flags.append("label_implies_loss")
        value = -value
    return value, flags


def _extract_cells_from_line(block: ExtractedBlock) -> list[ExtractedCell]:
    """Parse a single-line block into label/value cells."""
    text = block.text.strip()
    if not text:
        return []

    # Table rows already separated by pipes are the most reliable structure.
    if " | " in text:
        parts = [c.strip() for c in text.split(" | ")]
        if len(parts) >= 2:
            label = parts[0]
            values = parts[1:]
        else:
            return []
    else:
        # For free text lines, split on multiple spaces/tabs and separate the
        # leading label from the trailing numeric value(s).
        matches = list(NUMBER_PATTERN.finditer(text))
        if not matches:
            return []
        # Label is everything before the first numeric token.
        first_match = matches[0]
        label = text[: first_match.start()].strip()
        values = [m.group(0).strip() for m in matches]
        if not label:
            return []

    account, score, _alias = _match_account(label)
    cells: list[ExtractedCell] = []
    for raw_value in values:
        if _parse_value_token(raw_value) is None:
            continue
        cells.append(
            ExtractedCell(
                label=label,
                raw_value=raw_value,
                period=None,
                account=account,
                match_score=score,
                block=block,
            )
        )
    return cells


def _table_key(block: ExtractedBlock) -> tuple[str | None, str, int]:
    """Group table blocks by sheet/source/table id."""
    table_id = 0
    cell_range = block.cell_range or ""
    if cell_range.startswith("T") and ":" in cell_range:
        # Docx table: T{table}:R{row}
        with contextlib.suppress(ValueError):
            table_id = int(cell_range.split(":")[0][1:])
    return (block.sheet, block.source, table_id)


def _row_number(block: ExtractedBlock) -> int:
    """Extract row number from cell_range for sorting."""
    cell_range = block.cell_range or "0"
    # XLSX/CSV: "{row}:{row}"
    # Docx: "T{n}:R{row}"
    for part in reversed(cell_range.split(":")):
        if part.startswith("R"):
            try:
                return int(part[1:])
            except ValueError:
                pass
        try:
            return int(part)
        except ValueError:
            pass
    return 0


def _is_period_cell(cell: str) -> str | None:
    """Return a normalized period string if the cell looks like a period header."""
    text = cell.strip()
    if not text:
        return None
    # Common patterns: 2025, FY2025, Q1 2025, Dec 31, 2025, 2025-12-31
    # For now we extract a year or quarter-year token.
    if re.fullmatch(r"\d{4}", text):
        return text
    quarter = re.search(r"(Q[1-4]).*?(\d{4})", text, re.I)
    if quarter:
        return f"{quarter.group(2)} {quarter.group(1).upper()}"
    fiscal = re.search(r"FY\s*(\d{4})", text, re.I)
    if fiscal:
        return fiscal.group(1)
    year_month = re.search(r"(\d{4})[-/](\d{2})", text)
    if year_month:
        return f"{year_month.group(1)}-{year_month.group(2)}"
    return None


def _parse_table_rows(blocks: list[ExtractedBlock]) -> list[ExtractedCell]:
    """Reconstruct a table from row blocks and parse labels, periods, and values."""
    rows: list[list[str]] = []
    for block in sorted(blocks, key=_row_number):
        if " | " in block.text:
            rows.append([c.strip() for c in block.text.split(" | ")])
        else:
            rows.append([block.text.strip()])

    if not rows:
        return []

    # Detect header row: at least one non-first cell contains a period.
    header = rows[0]
    periods: dict[int, str | None] = {}
    has_period_header = False
    for idx, cell in enumerate(header[1:], start=1):
        period = _is_period_cell(cell)
        periods[idx] = period
        if period:
            has_period_header = True

    data_start = 1 if has_period_header else 0
    cells: list[ExtractedCell] = []
    for block, row in zip(blocks[data_start:], rows[data_start:], strict=False):
        if not row or not row[0].strip():
            continue
        label = row[0].strip()
        account, score, _ = _match_account(label)
        for col_idx, raw_value in enumerate(row[1:], start=1):
            period = periods.get(col_idx)
            if _parse_value_token(raw_value) is None:
                continue
            cells.append(
                ExtractedCell(
                    label=label,
                    raw_value=raw_value,
                    period=period,
                    account=account,
                    match_score=score,
                    block=block,
                )
            )
    return cells


def _extract_all_cells(document: ExtractedDocument) -> list[ExtractedCell]:
    """Extract every label/value cell from the document, preserving table structure."""
    table_blocks: dict[tuple[str | None, str, int], list[ExtractedBlock]] = defaultdict(list)
    line_blocks: list[ExtractedBlock] = []

    for block in document.blocks:
        if block.kind == "table-row":
            table_blocks[_table_key(block)].append(block)
        else:
            line_blocks.append(block)

    cells: list[ExtractedCell] = []
    for blocks in table_blocks.values():
        cells.extend(_parse_table_rows(blocks))
    for block in line_blocks:
        cells.extend(_extract_cells_from_line(block))
    return cells


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


def _metric_status(confidence: float, flags: tuple[str, ...]) -> str:
    if confidence < 0.95 or any(
        f in ("label_implies_loss", "positive_in_parens", "possible_european_thousands")
        for f in flags
    ):
        return "flagged_discrepancy"
    if confidence < 0.99 or flags:
        return "inferred"
    return "verified"


def _cell_to_metric(cell: ExtractedCell) -> Metric | None:
    if cell.account is None:
        return None
    parsed = _parse_value_token(cell.raw_value)
    if parsed is None:
        return None
    value, label_flags = _detect_negative_from_label(cell.label, parsed.value)
    flags = list(parsed.flags) + label_flags
    confidence = parsed.confidence * cell.match_score
    if label_flags:
        confidence *= 0.92
    confidence = round(max(0.0, min(1.0, confidence)), 4)
    status = _metric_status(confidence, tuple(flags))
    return Metric(
        key=cell.account.key,
        label=cell.account.label,
        value=value,
        unit="currency",
        period=cell.period,
        confidence=confidence,
        evidence=[_evidence(cell.block, text=cell.raw_value)],
        raw=cell.raw_value,
        status=status,
    )


def extract_metrics(document: ExtractedDocument) -> list[Metric]:
    """Extract metrics using the chart-of-accounts schema and table-aware parsing."""
    metrics: list[Metric] = []
    for cell in _extract_all_cells(document):
        metric = _cell_to_metric(cell)
        if metric is None:
            continue
        # If the same key is seen multiple times without a period, keep the
        # highest-confidence value. With periods, we keep all distinct periods.
        if metric.period is None:
            existing = next((m for m in metrics if m.key == metric.key and m.period is None), None)
            if existing is None or metric.confidence > existing.confidence:
                metrics = [m for m in metrics if not (m.key == metric.key and m.period is None)]
                metrics.append(metric)
        else:
            existing = next(
                (m for m in metrics if m.key == metric.key and m.period == metric.period), None
            )
            if existing is None or metric.confidence > existing.confidence:
                metrics = [
                    m for m in metrics if not (m.key == metric.key and m.period == metric.period)
                ]
                metrics.append(metric)
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
    raw = f"{numerator.raw} / {denominator.raw}" if numerator.raw and denominator.raw else ""
    return Metric(
        key=key,
        label=label,
        value=(numerator.value / denominator.value) * factor,
        unit=unit,
        period=numerator.period,
        confidence=min(numerator.confidence, denominator.confidence),
        evidence=[*numerator.evidence, *denominator.evidence],
        raw=raw,
        status=(
            "verified"
            if numerator.status == "verified" and denominator.status == "verified"
            else "inferred"
        ),
    )


def add_derived_metrics(metrics: list[Metric]) -> list[Metric]:
    """Compute derived ratios and imputed totals, grouped by period."""
    by_period: dict[str | None, dict[str, Metric]] = defaultdict(dict)
    for metric in metrics:
        by_period[metric.period][metric.key] = metric

    derived: list[Metric] = []
    for period, values in by_period.items():
        if (
            "total_liabilities" not in values
            and "total_liabilities_and_equity" in values
            and "equity" in values
        ):
            tle = values["total_liabilities_and_equity"]
            equity = values["equity"]
            derived.append(
                Metric(
                    key="total_liabilities",
                    label="Total liabilities",
                    value=tle.value - equity.value,
                    unit="currency",
                    period=period,
                    confidence=min(tle.confidence, equity.confidence),
                    evidence=[*tle.evidence, *equity.evidence],
                    raw=f"{tle.raw} - {equity.raw}",
                    status="inferred",
                )
            )

        specs = (
            ("gross_margin", "Gross margin", "gross_profit", "revenue", "percent"),
            ("net_margin", "Net margin", "net_income", "revenue", "percent"),
            ("current_ratio", "Current ratio", "current_assets", "current_liabilities", "ratio"),
            ("debt_to_equity", "Debt to equity", "debt", "equity", "ratio"),
        )
        for key, label, num_key, den_key, unit in specs:
            if num_key in values and den_key in values:
                result = _derived_metric(key, label, values[num_key], values[den_key], unit)
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


def numeric_rules(metrics: list[Metric]) -> list[Finding]:
    """Cross-validate accounting equations and risk thresholds per period."""
    by_period: dict[str | None, list[Metric]] = defaultdict(list)
    for metric in metrics:
        by_period[metric.period].append(metric)

    findings: list[Finding] = []
    for period, period_metrics in by_period.items():
        values = {metric.key: metric for metric in period_metrics}

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
                        f"Assets differ from liabilities plus equity by {difference:,.2f}"
                        + (f" for period {period}" if period else ""),
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
            expected = revenue.value - abs(cogs.value)
            difference = gross_profit.value - expected
            tolerance = max(abs(revenue.value) * 0.01, 1)
            if abs(difference) > tolerance:
                findings.append(
                    _finding(
                        "GROSS_PROFIT_MISMATCH",
                        "Gross profit is inconsistent",
                        "accounting-integrity",
                        Severity.HIGH,
                        f"Reported gross profit differs from revenue minus COGS by "
                        f"{difference:,.2f}"
                        + (f" for period {period}" if period else ""),
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
                    f"Net income is {metric.value:,.2f} for the extracted period"
                    + (f" {period}" if period else ""),
                    (
                        "Review expense drivers, one-time items, and cash runway with "
                        "the business owner."
                    ),
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
                    f"Current ratio is {metric.value:.2f}, below the 1.00 screening threshold"
                    + (f" for period {period}" if period else ""),
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
                        f"screening threshold"
                    )
                    + (f" for period {period}" if period else ""),
                    "Compare leverage with industry peers and inspect debt pricing and covenants.",
                    metric.evidence,
                    confidence=0.9,
                    requires_human_review=True,
                )
            )
    return findings


def _extraction_warning_findings(document: ExtractedDocument) -> list[Finding]:
    """Surface extraction warnings as reviewable findings with fixes."""
    findings: list[Finding] = []
    for index, warning in enumerate(document.warnings):
        findings.append(
            _finding(
                f"EXTRACTION_WARNING_{index}",
                "Extraction issue detected",
                "extraction-quality",
                Severity.MEDIUM,
                warning,
                "Re-export the document with selectable text or use a higher-resolution scan, then re-upload.",
                [_evidence(document.blocks[0])] if document.blocks else [],
                requires_human_review=True,
            )
        )
    return findings


def _quality_findings(document: ExtractedDocument, metrics: list[Metric]) -> list[Finding]:
    """Flag extraction-quality and document-quality issues that need human review."""
    findings: list[Finding] = []
    full_text = document.text.lower()

    if "unaudited" in full_text or "draft" in full_text:
        findings.append(
            _finding(
                "UNAUDITED_OR_DRAFT",
                "Document is marked unaudited or draft",
                "document-quality",
                Severity.MEDIUM,
                "The document contains 'unaudited' or 'draft' language.",
                "Treat figures as preliminary and confirm final audited values before use.",
                [_evidence(document.blocks[0], text=full_text[:500])] if document.blocks else [],
                requires_human_review=True,
            )
        )

    for metric in metrics:
        if metric.confidence < 0.95 or metric.status == "flagged_discrepancy":
            findings.append(
                _finding(
                    f"LOW_CONFIDENCE_{metric.key.upper()}",
                    f"Low confidence on {metric.label}",
                    "extraction-quality",
                    Severity.HIGH if metric.status == "flagged_discrepancy" else Severity.MEDIUM,
                    f"Confidence for {metric.label} ({metric.raw!r}) is {metric.confidence:.0%}.",
                    "Verify the raw value, sign, and period against the source document.",
                    metric.evidence,
                    confidence=metric.confidence,
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
    """End-to-end schema-driven financial extraction and risk analysis."""
    metrics = add_derived_metrics(extract_metrics(document))
    findings: list[Finding] = []
    findings.extend(_extraction_warning_findings(document))
    findings.extend(numeric_rules(metrics))
    findings.extend(_quality_findings(document, metrics))
    findings.extend(_text_rules(document))
    # Deduplicate by key+period, preferring the highest-confidence occurrence.
    deduplicated: dict[tuple[str, str | None], Metric] = {}
    for metric in metrics:
        key = (metric.key, metric.period)
        existing = deduplicated.get(key)
        if existing is None or metric.confidence > existing.confidence:
            deduplicated[key] = metric
    return list(deduplicated.values()), findings
