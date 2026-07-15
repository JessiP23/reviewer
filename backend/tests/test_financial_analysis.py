import pytest

from reviewer.analysis.financial import NUMBER_PATTERN, analyze, parse_number
from reviewer.extraction import ExtractorRegistry


@pytest.mark.parametrize(
    ("source", "expected"),
    [("$1.2M", 1_200_000), ("(2,500)", -2_500), ("75k", 75_000), ("-42", -42)],
)
def test_parse_number(source: str, expected: float) -> None:
    match = NUMBER_PATTERN.search(source)
    assert match is not None
    assert parse_number(match) == expected


def test_detects_balance_sheet_and_liquidity_risks() -> None:
    content = b"""Total current assets,80000
Total current liabilities,100000
Total assets,500000
Total liabilities,350000
Owners' equity,100000
Total debt,300000
Revenue,1000000
Cost of goods sold,700000
Gross profit,250000
Net income,-50000
"""
    document = ExtractorRegistry().extract("financials.csv", content)
    metrics, findings = analyze(document)

    metric_values = {metric.key: metric.value for metric in metrics}
    codes = {finding.code for finding in findings}
    assert metric_values["current_ratio"] == pytest.approx(0.8)
    assert metric_values["debt_to_equity"] == pytest.approx(3)
    assert "BALANCE_SHEET_MISMATCH" in codes
    assert "GROSS_PROFIT_MISMATCH" in codes
    assert "NEGATIVE_NET_INCOME" in codes
    assert "LOW_CURRENT_RATIO" in codes
    assert "HIGH_DEBT_TO_EQUITY" in codes
    assert all(finding.evidence for finding in findings)


def test_detects_textual_risks_with_source_evidence() -> None:
    document = ExtractorRegistry().extract(
        "notes.txt",
        (
            b"The auditor identified a material weakness. "
            b"There is substantial doubt about going concern."
        ),
    )
    _, findings = analyze(document)
    assert {finding.code for finding in findings} == {
        "MATERIAL_WEAKNESS",
        "GOING_CONCERN_LANGUAGE",
    }
    assert findings[0].evidence[0].source == "notes.txt"


def test_redacts_sensitive_evidence() -> None:
    document = ExtractorRegistry().extract("payroll.txt", b"Owner SSN: 123-45-6789")
    _, findings = analyze(document)
    assert findings[0].code == "PII_SSN"
    assert "123-45-6789" not in findings[0].evidence[0].text
