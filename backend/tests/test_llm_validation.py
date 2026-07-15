from reviewer.analysis.llm import ModelFinding, ModelResponse, validate_model_findings
from reviewer.domain.models import Severity
from reviewer.extraction import ExtractorRegistry


def candidate(evidence: str, explanation: str) -> ModelFinding:
    return ModelFinding(
        title="Revenue concentration",
        category="profitability",
        severity=Severity.MEDIUM,
        explanation=explanation,
        recommendation="Validate this result with the complete source statement.",
        evidence_quote=evidence,
        confidence=0.97,
    )


def test_accepts_only_grounded_model_findings() -> None:
    document = ExtractorRegistry().extract("note.txt", b"Revenue declined by 12% this year.")
    response = ModelResponse(
        findings=[
            candidate("Revenue declined by 12% this year.", "Revenue declined by 12%."),
            candidate("A quote that does not exist.", "Revenue declined by 40%."),
            candidate("Revenue declined by 12% this year.", "Revenue declined by 40%."),
        ]
    )

    findings = validate_model_findings(document, response)

    assert len(findings) == 1
    assert findings[0].confidence == 0.85
    assert findings[0].requires_human_review is True

