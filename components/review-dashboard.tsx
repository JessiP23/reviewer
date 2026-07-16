"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { graphql, useLazyLoadQuery } from "react-relay";

import type { reviewDashboardQuery } from "@/__generated__/reviewDashboardQuery.graphql";
import { apiUrl } from "@/lib/relay/environment";

const DashboardQuery = graphql`
  query reviewDashboardQuery {
    reviews(first: 30) {
      id
      filename
      status
      ruleVersion
      createdAt
      error
      diagnostics {
        parser
        blocks
        characters
        coverage
        warnings
      }
      metrics {
        key
        label
        value
        unit
        confidence
      }
      findings {
        code
        title
        category
        severity
        explanation
        recommendation
        confidence
        requiresHumanReview
        evidence {
          text
          source
          page
          sheet
          cellRange
        }
      }
    }
  }
`;

const TERMINAL = new Set(["completed", "needs_review", "failed"]);

function formatMetric(value: number, unit: string) {
  if (unit === "percent") return `${value.toFixed(1)}%`;
  if (unit === "ratio") return `${value.toFixed(2)}×`;
  if (unit === "currency") {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: Math.abs(value) >= 1_000_000 ? "compact" : "standard",
      maximumFractionDigits: 1,
    }).format(value);
  }
  return value.toLocaleString();
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export function ReviewDashboard() {
  const [fetchKey, setFetchKey] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const data = useLazyLoadQuery<reviewDashboardQuery>(
    DashboardQuery,
    {},
    { fetchKey, fetchPolicy: "network-only" },
  );
  const reviews = data.reviews;
  const selected = useMemo(
    () => reviews.find((review) => review.id === selectedId) ?? reviews[0] ?? null,
    [reviews, selectedId],
  );

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  function pollReview(reviewId: string) {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    pollTimerRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${apiUrl}/graphql`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            query: "query ReviewStatus($id: ID!) { review(id: $id) { status } }",
            variables: { id: reviewId },
          }),
        });
        const payload = await response.json();
        const status = payload.data?.review?.status;
        setFetchKey((value) => value + 1);
        if (TERMINAL.has(status)) {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
      } catch {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    }, 1500);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = inputRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${apiUrl}/v1/reviews`, { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Upload failed");
      setSelectedId(payload.id);
      setFetchKey((value) => value + 1);
      pollReview(payload.id);
      if (inputRef.current) inputRef.current.value = "";
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <div className="eyebrow"><span className="signal" /> Evidence-first financial intelligence</div>
        <div className="hero-grid">
          <div>
            <h1>Know what the numbers<br /><em>are trying to tell you.</em></h1>
            <p className="hero-copy">
              Review SMB financial statements for integrity, liquidity, leverage, profitability,
              and sensitive disclosures—with every alert tied back to its source.
            </p>
          </div>
          <form className="upload-card" onSubmit={handleUpload}>
            <label htmlFor="financial-file">Add a financial document</label>
            <p>PDF, XLSX, CSV, DOCX, Markdown, or text · 4 MB on AWS, 10 MB locally</p>
            <div className="upload-row">
              <input ref={inputRef} id="financial-file" type="file" accept=".pdf,.xlsx,.csv,.docx,.md,.txt,.json" required />
              <button type="submit" disabled={uploading}>{uploading ? "Reviewing…" : "Start review"}</button>
            </div>
            {uploadError && <p className="form-error" role="alert">{uploadError}</p>}
          </form>
        </div>
      </section>

      <section className="workspace" aria-label="Review workspace">
        <aside className="review-list">
          <div className="section-heading">
            <div><span className="kicker">Workspace</span><h2>Recent reviews</h2></div>
            <span className="count">{reviews.length}</span>
          </div>
          {reviews.length === 0 ? (
            <div className="empty-state">Upload your first statement to create an auditable review.</div>
          ) : reviews.map((review) => (
            <button
              type="button"
              className={`review-row ${selected?.id === review.id ? "active" : ""}`}
              key={review.id}
              onClick={() => setSelectedId(review.id)}
            >
              <span className={`status-dot ${review.status}`} />
              <span className="review-name">{review.filename}</span>
              <span className="review-status">{statusLabel(review.status)}</span>
              <span className="review-date">{new Date(review.createdAt).toLocaleDateString()}</span>
            </button>
          ))}
        </aside>

        <div className="review-detail">
          {!selected ? (
            <div className="detail-empty"><span>01</span><h2>Your analysis will appear here.</h2><p>Source-linked findings. Clear confidence. No black-box certainty.</p></div>
          ) : (
            <>
              <header className="detail-header">
                <div><span className="kicker">Financial review</span><h2>{selected.filename}</h2></div>
                <span className={`status-pill ${selected.status}`}>{statusLabel(selected.status)}</span>
              </header>

              {selected.error && <div className="error-panel"><strong>Review stopped</strong><p>{selected.error}</p></div>}

              {selected.metrics.length > 0 && (
                <section className="metrics" aria-label="Extracted metrics">
                  {selected.metrics.slice(0, 8).map((metric) => (
                    <article className="metric" key={metric.key}>
                      <span>{metric.label}</span>
                      <strong>{formatMetric(metric.value, metric.unit)}</strong>
                      <small>{Math.round(metric.confidence * 100)}% extraction confidence</small>
                    </article>
                  ))}
                </section>
              )}

              <section className="findings-section">
                <div className="section-heading findings-heading">
                  <div><span className="kicker">Risk signals</span><h2>{selected.findings.length} findings</h2></div>
                  {selected.diagnostics && <span className="parser">{selected.diagnostics.parser} · {Math.round(selected.diagnostics.coverage * 100)}% coverage</span>}
                </div>
                {selected.findings.length === 0 && TERMINAL.has(selected.status) ? (
                  <div className="no-findings"><span>✓</span><div><strong>No configured risk signals found</strong><p>This is not a guarantee of financial accuracy. Review coverage and source documents before acting.</p></div></div>
                ) : selected.findings.map((finding) => (
                  <article className={`finding ${finding.severity}`} key={finding.code}>
                    <div className="finding-index">{finding.severity}</div>
                    <div className="finding-body">
                      <div className="finding-title"><h3>{finding.title}</h3><span>{finding.category}</span></div>
                      <p>{finding.explanation}</p>
                      <p className="recommendation"><strong>Next step</strong> {finding.recommendation}</p>
                      {finding.evidence[0] && (
                        <details>
                          <summary>View source evidence · {Math.round(finding.confidence * 100)}% confidence</summary>
                          <blockquote>“{finding.evidence[0].text}”</blockquote>
                          <small>{finding.evidence[0].source}{finding.evidence[0].sheet ? ` · ${finding.evidence[0].sheet}` : ""}{finding.evidence[0].page ? ` · page ${finding.evidence[0].page}` : ""}</small>
                        </details>
                      )}
                    </div>
                  </article>
                ))}
              </section>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
