from __future__ import annotations

import re
from difflib import SequenceMatcher

from reviewer.domain.models import Finding, Metric, Review


class ReviewChatService:
    """Answer questions using only the structured review context.

    The deterministic responder keeps every answer grounded in the extracted
    metrics, findings, and evidence of a single review.
    """

    async def answer(self, review: Review, question: str) -> str:
        return self._answer_from_context(review, question)

    def _normalize(self, text: str) -> str:
        return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, self._normalize(a), self._normalize(b)).ratio()

    def _match_score(self, query: str, candidate: str) -> float:
        query_norm = self._normalize(query)
        cand_norm = self._normalize(candidate)
        if not query_norm or not cand_norm:
            return 0.0
        if cand_norm in query_norm or query_norm in cand_norm:
            return 1.0
        full = self._similarity(query_norm, cand_norm)
        words = query_norm.split()
        best_word = max((self._similarity(w, cand_norm) for w in words), default=0.0)
        return max(full, best_word)

    def _format_metric_value(self, metric: Metric) -> str:
        if metric.unit == "currency":
            return f"${metric.value:,.2f}"
        if metric.unit == "percent":
            return f"{metric.value:.1f}%"
        if metric.unit == "ratio":
            return f"{metric.value:.2f}x"
        return f"{metric.value:,.2f}"

    def _format_metric(self, metric: Metric) -> str:
        parts = [
            f"{metric.label}: {self._format_metric_value(metric)}",
            f"confidence {int(metric.confidence * 100)}%",
        ]
        if metric.status:
            parts.append(f"status {metric.status}")
        if metric.raw:
            parts.append(f"raw {metric.raw!r}")
        if metric.period:
            parts.append(f"period {metric.period}")
        return "; ".join(parts)

    def _format_finding(self, finding: Finding) -> str:
        lines = [
            f"{finding.title} ({finding.severity})",
            finding.explanation,
        ]
        if finding.recommendation:
            lines.append(f"Fix: {finding.recommendation}")
        if finding.evidence:
            evidence_texts = []
            for ev in finding.evidence:
                ref = ev.source
                if ev.page:
                    ref += f", page {ev.page}"
                if ev.sheet:
                    ref += f", sheet {ev.sheet}"
                if ev.cell_range:
                    ref += f", {ev.cell_range}"
                evidence_texts.append(f"  {ref}: {ev.text[:200]}")
            lines.append("Evidence:")
            lines.extend(evidence_texts)
        return "\n".join(lines)

    def _find_metric(self, review: Review, query: str) -> Metric | None:
        best: Metric | None = None
        best_score = 0.6
        for metric in review.metrics:
            for candidate in (metric.label, metric.key, metric.raw or ""):
                score = self._match_score(query, candidate)
                if score > best_score:
                    best_score = score
                    best = metric
        return best

    def _find_finding(self, review: Review, query: str) -> Finding | None:
        best: Finding | None = None
        best_score = 0.6
        for finding in review.findings:
            for candidate in (finding.title, finding.code, finding.category):
                score = self._match_score(query, candidate)
                if score > best_score:
                    best_score = score
                    best = finding
        return best

    def _answer_from_context(self, review: Review, question: str) -> str:
        q = self._normalize(question)

        # Summary / overview / what did you find
        if any(
            word in q
            for word in (
                "summary",
                "overview",
                "what did you find",
                "tell me",
                "describe",
                "results",
            )
        ):
            return self._summary(review)

        # Flags / issues / findings / needs review
        if any(
            word in q
            for word in (
                "flag",
                "issue",
                "problem",
                "finding",
                "risk",
                "needs review",
                "discrepancy",
            )
        ):
            return self._flags(review)

        # All metrics / numbers / extracted data
        if any(
            phrase in q
            for phrase in ("metrics", "numbers", "extracted", "all values", "what did you extract")
        ):
            return self._metrics_list(review)

        # Document / file questions
        if any(word in q for word in ("document", "file", "uploaded", "filename")):
            return (
                f"The uploaded document is {review.filename!r}. "
                f"Status: {review.status.value}. "
                f"I extracted {len(review.metrics)} metrics and found "
                f"{len(review.findings)} finding(s)."
            )

        # Evidence / source / where questions
        if any(word in q for word in ("evidence", "source", "where", "page", "location")):
            metric = self._find_metric(review, q)
            if metric:
                return self._evidence_for_metric(metric)
            finding = self._find_finding(review, q)
            if finding:
                return self._evidence_for_finding(finding)

        # Confidence questions
        if "confidence" in q:
            metric = self._find_metric(review, q)
            if metric:
                conf = int(metric.confidence * 100)
                status = metric.status or "unknown"
                return (
                    f"{metric.label} has an extraction confidence of {conf}% "
                    f"and status {status}."
                )
            low = [m for m in review.metrics if m.confidence < 0.95]
            if low:
                return "Low-confidence metrics: " + "; ".join(
                    f"{m.label} ({int(m.confidence * 100)}%)" for m in low
                )
            return "All extracted metrics have confidence of 95% or higher."

        # Look for a specific finding first
        finding = self._find_finding(review, q)
        if finding:
            return self._format_finding(finding)

        # Look for a specific metric
        metric = self._find_metric(review, q)
        if metric:
            return self._answer_metric(review, metric)

        # Health / is it good questions
        if any(
            word in q
            for word in ("healthy", "good", "bad", "risky", "safe", "leverage", "liquidity")
        ):
            return self._health_answer(review, q)

        return (
            "I can only answer from the review context. "
            "Try asking about a metric (e.g., revenue), a finding, "
            "what was flagged, or request a summary."
        )

    def _summary(self, review: Review) -> str:
        flagged_metrics = [m for m in review.metrics if m.status and m.status != "verified"]
        needs_review = [f for f in review.findings if f.requires_human_review]
        lines = [
            (
                f"I reviewed {review.filename!r} and extracted {len(review.metrics)} metrics "
                f"with {len(review.findings)} finding(s)."
            ),
        ]
        if flagged_metrics:
            lines.append(
                "Metrics that need attention: " + ", ".join(m.label for m in flagged_metrics)
            )
        if needs_review:
            lines.append(f"{len(needs_review)} finding(s) require human review.")
        if not flagged_metrics and not needs_review:
            lines.append("Nothing in the review is flagged for human review.")
        return " ".join(lines)

    def _flags(self, review: Review) -> str:
        flagged_metrics = [m for m in review.metrics if m.status and m.status != "verified"]
        needs_review = [f for f in review.findings if f.requires_human_review]
        if not flagged_metrics and not needs_review:
            return "No metrics or findings are currently flagged for human review."
        parts = []
        if flagged_metrics:
            parts.append(
                "Flagged metrics: " + "; ".join(self._format_metric(m) for m in flagged_metrics)
            )
        if needs_review:
            parts.append("Findings needing review:")
            for finding in needs_review:
                parts.append(self._format_finding(finding))
        return "\n\n".join(parts)

    def _metrics_list(self, review: Review) -> str:
        if not review.metrics:
            return "No metrics were extracted from this document."
        return "\n".join(self._format_metric(m) for m in review.metrics)

    def _answer_metric(self, review: Review, metric: Metric) -> str:
        answer = f"{metric.label} is {self._format_metric_value(metric)}"
        if metric.period:
            answer += f" for {metric.period}"
        answer += (
            f" (confidence {int(metric.confidence * 100)}%, status {metric.status or 'unknown'})."
        )

        # Add context-aware observations from findings
        if metric.key == "current_ratio":
            if any(f.code == "LOW_CURRENT_RATIO" for f in review.findings):
                answer += " The review flags this as below the 1.00 threshold."
            else:
                answer += " The review did not flag short-term liquidity pressure."
        if metric.key == "debt_to_equity":
            if any(f.code == "HIGH_DEBT_TO_EQUITY" for f in review.findings):
                answer += " The review flags this as elevated leverage."
            else:
                answer += " The review did not flag elevated leverage."
        return answer

    def _evidence_for_metric(self, metric: Metric) -> str:
        if not metric.evidence:
            return (
                f"{metric.label}: {self._format_metric_value(metric)}. "
                f"No direct evidence was recorded for this metric."
            )
        lines = [f"{metric.label}: {self._format_metric_value(metric)}"]
        for ev in metric.evidence:
            ref = ev.source
            if ev.page:
                ref += f", page {ev.page}"
            if ev.sheet:
                ref += f", sheet {ev.sheet}"
            if ev.cell_range:
                ref += f", {ev.cell_range}"
            lines.append(f"Source: {ref}")
            lines.append(f"Text: {ev.text[:250]}")
        return "\n".join(lines)

    def _evidence_for_finding(self, finding: Finding) -> str:
        return self._format_finding(finding)

    def _health_answer(self, review: Review, query: str) -> str:
        q = self._normalize(query)
        metric = self._find_metric(review, query)
        if metric:
            return self._answer_metric(review, metric)

        if any(word in q for word in ("leverage", "debt", "solvency")):
            de = next((m for m in review.metrics if m.key == "debt_to_equity"), None)
            if de:
                return self._answer_metric(review, de)

        if any(word in q for word in ("liquidity", "current ratio", "short term")):
            cr = next((m for m in review.metrics if m.key == "current_ratio"), None)
            if cr:
                return self._answer_metric(review, cr)

        if any(word in q for word in ("profit", "profitability", "margin", "net income")):
            nm = next((m for m in review.metrics if m.key == "net_margin"), None)
            gm = next((m for m in review.metrics if m.key == "gross_margin"), None)
            if nm or gm:
                return "\n".join(self._answer_metric(review, m) for m in (gm, nm) if m)

        if any(word in q for word in ("balance", "balance sheet")):
            mismatch = next(
                (f for f in review.findings if f.code == "BALANCE_SHEET_MISMATCH"), None
            )
            if mismatch:
                return self._format_finding(mismatch)
            return "The balance sheet reconciled within tolerance."

        needs_review = [f for f in review.findings if f.requires_human_review]
        if needs_review:
            return "The review has items that need attention:\n" + "\n".join(
                f"- {f.title} ({f.severity})" for f in needs_review
            )
        return "The review found no items that require human review."
