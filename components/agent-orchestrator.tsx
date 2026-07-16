"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bot, Loader2, Paperclip, RotateCcw, Send, User, X } from "lucide-react";

import { apiUrl } from "@/lib/relay/environment";

type AgentState = "idle" | "running" | "review" | "completed" | "failed";

type Evidence = {
  text: string;
  source: string;
  page?: number | null;
  sheet?: string | null;
  cellRange?: string | null;
};

type Finding = {
  code: string;
  title: string;
  category: string;
  severity: string;
  explanation: string;
  recommendation: string;
  confidence: number;
  requiresHumanReview: boolean;
  evidence: Evidence[];
};

type Metric = {
  key: string;
  label: string;
  value: number;
  unit: string;
  confidence: number;
  raw?: string | null;
  status?: string | null;
  period?: string | null;
};

type Review = {
  id: string;
  filename: string;
  status: string;
  ruleVersion: string;
  createdAt: string;
  updatedAt: string;
  error: string | null;
  humanFeedback: string | null;
  humanDecision: string | null;
  diagnostics: {
    parser: string;
    blocks: number;
    characters: number;
    coverage: number;
    warnings: string[];
  } | null;
  metrics: Metric[];
  findings: Finding[];
};

type Message = {
  role: "user" | "ai";
  text: string;
};

const REVIEW_QUERY = `
  query AgentReview($id: ID!) {
    review(id: $id) {
      id
      filename
      status
      ruleVersion
      createdAt
      updatedAt
      error
      humanFeedback
      humanDecision
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
        raw
        status
        period
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

const TERMINAL_STATUSES = new Set(["completed", "needs_review", "rejected", "failed"]);

function formatMetric(value: number, unit: string) {
  if (unit === "percent") return `${value.toFixed(1)}%`;
  if (unit === "ratio") return `${value.toFixed(2)}x`;
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

function buildReviewMessage(review: Review): string {
  const needsReview = review.findings.filter((f) => f.requiresHumanReview);
  if (needsReview.length === 0) {
    return `I've analyzed ${review.filename}. No items need your review.`;
  }
  return `I've analyzed ${review.filename} and found ${needsReview.length} item(s) that need your review.`;
}

function buildSummaryMessage(review: Review): string {
  const needsReview = review.findings.filter((f) => f.requiresHumanReview);
  let text = `Review complete for ${review.filename}. I extracted ${review.metrics.length} metrics and found ${review.findings.length} issue(s).`;
  if (needsReview.length > 0) {
    text += ` ${needsReview.length} still require human review.`;
  } else {
    text += " Nothing needs manual review.";
  }
  return text;
}

export function AgentOrchestrator() {
  const [state, setState] = useState<AgentState>("idle");
  const [review, setReview] = useState<Review | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [acting, setActing] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "ai",
      text:
        "Hi, I'm your financial review assistant. Upload a PDF, spreadsheet, or text file and I'll analyze it for you.",
    },
  ]);

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastStatusRef = useRef<string | null>(null);

  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const documentUrl = useMemo(
    () => (review ? `${apiUrl}/v1/reviews/${review.id}/document` : null),
    [review],
  );

  const append = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    setState("idle");
    setReview(null);
    setError(null);
    setFeedback("");
    setFile(null);
    lastStatusRef.current = null;
    setMessages([
      {
        role: "ai",
        text:
          "Hi, I'm your financial review assistant. Upload a PDF, spreadsheet, or text file and I'll analyze it for you.",
      },
    ]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [stopPolling]);

  const fetchReview = useCallback(
    async (id: string) => {
      try {
        const response = await fetch(`${apiUrl}/graphql`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ query: REVIEW_QUERY, variables: { id } }),
        });
        const payload = await response.json();
        if (payload.errors?.length) {
          throw new Error(payload.errors[0].message);
        }
        const fetched = payload.data?.review as Review | null;
        if (!fetched) {
          throw new Error("Review not found");
        }

        setReview(fetched);

        if (fetched.status === "failed") {
          setError(fetched.error ?? "Review failed");
          setState("failed");
          if (lastStatusRef.current !== fetched.status) {
            lastStatusRef.current = fetched.status;
            append({
              role: "ai",
              text: `I wasn't able to complete the review. ${fetched.error ?? "Review failed"}`,
            });
          }
        } else if (fetched.status === "needs_review") {
          setState("review");
          if (lastStatusRef.current !== fetched.status) {
            lastStatusRef.current = fetched.status;
            append({ role: "ai", text: buildReviewMessage(fetched) });
          }
        } else if (fetched.status === "completed" || fetched.status === "rejected") {
          setState("completed");
          if (lastStatusRef.current !== fetched.status) {
            lastStatusRef.current = fetched.status;
            append({ role: "ai", text: buildSummaryMessage(fetched) });
          }
        } else {
          setState("running");
        }

        return fetched;
      } catch (err) {
        stopPolling();
        setReview(null);
        setError(err instanceof Error ? err.message : "Failed to load review");
        setState("failed");
        append({
          role: "ai",
          text: `Something went wrong: ${err instanceof Error ? err.message : "Failed to load review"}`,
        });
        return null;
      }
    },
    [append, stopPolling]
  );

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;

    append({ role: "user", text: `Uploaded ${file.name}` });
    setUploading(true);
    setError(null);
    setReview(null);
    setFeedback("");
    setState("running");
    lastStatusRef.current = null;

    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${apiUrl}/v1/reviews`, { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Upload failed");
      const id = payload.id as string;
      await fetchReview(id);
    } catch (err) {
      stopPolling();
      setReview(null);
      setError(err instanceof Error ? err.message : "Upload failed");
      setState("failed");
      append({
        role: "ai",
        text: `Upload failed: ${err instanceof Error ? err.message : "Upload failed"}`,
      });
    } finally {
      setUploading(false);
    }
  }

  async function handleChatSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!review || !chatInput.trim()) return;

    const question = chatInput.trim();
    setChatInput("");
    append({ role: "user", text: question });
    setChatLoading(true);

    try {
      const response = await fetch(`${apiUrl}/v1/reviews/${review.id}/chat`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: question }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Chat failed");
      append({ role: "ai", text: payload.reply });
    } catch (err) {
      append({
        role: "ai",
        text: `I couldn't answer that: ${err instanceof Error ? err.message : "Chat failed"}`,
      });
    } finally {
      setChatLoading(false);
    }
  }

  async function submitDecision(decision: "approved" | "rejected") {
    if (!review) return;
    setActing(true);

    const note = feedback.trim();
    append({
      role: "user",
      text: decision === "approved" ? `Approve${note ? `: ${note}` : ""}` : `Reject${note ? `: ${note}` : ""}`,
    });

    try {
      const endpoint = decision === "approved" ? "approve" : "reject";
      const response = await fetch(`${apiUrl}/v1/reviews/${review.id}/${endpoint}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ feedback: note || null }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? `Failed to ${decision}`);
      await fetchReview(review.id);
    } catch (err) {
      stopPolling();
      setReview(null);
      setError(err instanceof Error ? err.message : `Failed to ${decision}`);
      setState("failed");
      append({
        role: "ai",
        text: `I couldn't submit your decision: ${err instanceof Error ? err.message : `Failed to ${decision}`}`,
      });
    } finally {
      setActing(false);
    }
  }

  useEffect(() => {
    if (!review || !review.id || TERMINAL_STATUSES.has(review.status)) {
      stopPolling();
      return;
    }
    const id = review.id;
    pollTimerRef.current = setInterval(() => fetchReview(id), 1500);
    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [review?.id, review?.status, fetchReview, stopPolling]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return (
    <div className="h-screen bg-slate-900 text-slate-100 flex flex-col font-sans overflow-hidden">
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-cyan-500/10 text-cyan-400">
            <Bot size={20} />
          </div>
          <div>
            <h1 className="font-semibold">AI Review</h1>
            <p className="text-xs text-slate-400">Upload a document to get started</p>
          </div>
        </div>
        {state !== "idle" && (
          <button
            type="button"
            onClick={reset}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-full border border-slate-700 text-slate-300 hover:text-slate-100 hover:border-slate-500 transition-colors"
          >
            <RotateCcw size={14} />
            New review
          </button>
        )}
      </header>

      <main className="flex-1 overflow-hidden flex flex-col">
        {state === "idle" ? (
          <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-semibold">AI Review</h2>
              <p className="text-slate-400">Upload a financial document to get a source-linked review.</p>
            </div>
            <p className="text-sm text-slate-500">PDF, XLSX, CSV, DOCX, MD, TXT, JSON</p>
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">
            <div className="w-1/2 flex flex-col border-r border-slate-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs text-slate-400">Reviewing</p>
                  <h3 className="font-semibold text-sm truncate">{review?.filename}</h3>
                </div>
                {review && <ReviewStatusPill status={review.status} />}
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {state === "running" && (
                  <div className="flex items-start gap-3">
                    <div className="shrink-0 p-2 rounded-full bg-slate-800 text-cyan-400">
                      <Bot size={16} />
                    </div>
                    <div className="flex items-center gap-2 mt-2 text-slate-400">
                      <Loader2 size={16} className="animate-spin" />
                      <span className="text-sm">Analyzing your document…</span>
                    </div>
                  </div>
                )}

                {state === "review" && review && (
                  <ReviewPanel
                    review={review}
                    feedback={feedback}
                    onFeedbackChange={setFeedback}
                    onApprove={() => submitDecision("approved")}
                    onReject={() => submitDecision("rejected")}
                    acting={acting}
                  />
                )}

                {state === "completed" && review && <SummaryPanel review={review} onRestart={reset} />}

                {state === "failed" && error && <ErrorPanel error={error} onRestart={reset} />}
              </div>

              <div className="h-80 border-t border-slate-800 flex flex-col shrink-0">
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.map((message, index) => (
                    <MessageBubble key={index} message={message} />
                  ))}

                  {chatLoading && (
                    <div className="flex items-start gap-3">
                      <div className="shrink-0 p-2 rounded-full bg-slate-800 text-cyan-400">
                        <Bot size={16} />
                      </div>
                      <div className="flex items-center gap-2 mt-2 text-slate-400">
                        <Loader2 size={16} className="animate-spin" />
                        <span className="text-sm">Thinking…</span>
                      </div>
                    </div>
                  )}

                  <div ref={bottomRef} />
                </div>

                <ChatComposer
                  input={chatInput}
                  onChange={setChatInput}
                  onSubmit={handleChatSubmit}
                  loading={chatLoading}
                />
              </div>
            </div>

            <div className="w-1/2 h-full bg-slate-950 overflow-hidden relative">
              {documentUrl ? (
                <object data={documentUrl} type="application/pdf" className="w-full h-full">
                  <div className="p-6 text-slate-400">
                    Preview not available.{" "}
                    <a
                      href={documentUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:underline"
                    >
                      Open document
                    </a>
                  </div>
                </object>
              ) : (
                <div className="flex h-full items-center justify-center text-slate-500">
                  No document preview
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {state === "idle" && (
        <Composer
          file={file}
          onFileChange={setFile}
          onSubmit={handleUpload}
          uploading={uploading}
          inputRef={fileInputRef}
        />
      )}
    </div>
  );
}

function ReviewStatusPill({ status }: { status: string }) {
  const label = status.replaceAll("_", " ");
  const color =
    status === "completed"
      ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
      : status === "needs_review"
        ? "text-amber-400 bg-amber-400/10 border-amber-400/20"
        : status === "failed" || status === "rejected"
          ? "text-rose-400 bg-rose-400/10 border-rose-400/20"
          : "text-cyan-400 bg-cyan-400/10 border-cyan-400/20";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider border ${color}`}>
      {label}
    </span>
  );
}

function ChatComposer({
  input,
  onChange,
  onSubmit,
  loading,
}: {
  input: string;
  onChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
  loading: boolean;
}) {
  return (
    <form onSubmit={onSubmit} className="border-t border-slate-800 bg-slate-900 p-4">
      <div className="max-w-2xl mx-auto flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-800/50 px-4 py-3">
        <input
          type="text"
          value={input}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Ask about this review…"
          className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-500 text-slate-900 font-semibold hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          {loading ? "…" : "Send"}
        </button>
      </div>
    </form>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`shrink-0 p-2 rounded-full ${
          isUser ? "bg-cyan-500 text-slate-900" : "bg-slate-800 text-cyan-400"
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-cyan-500 text-slate-900 rounded-tr-none"
            : "bg-slate-800 text-slate-100 rounded-tl-none"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.text}</p>
      </div>
    </div>
  );
}

function Composer({
  file,
  onFileChange,
  onSubmit,
  uploading,
  inputRef,
}: {
  file: File | null;
  onFileChange: (file: File | null) => void;
  onSubmit: (event: React.FormEvent) => void;
  uploading: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  return (
    <form onSubmit={onSubmit} className="border-t border-slate-800 bg-slate-900 p-4">
      <div className="max-w-2xl mx-auto flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-800/50 px-4 py-3">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="shrink-0 p-2 rounded-full text-slate-400 hover:text-slate-100 hover:bg-slate-700 transition-colors"
          aria-label="Attach file"
        >
          <Paperclip size={18} />
        </button>

        <input
          ref={inputRef}
          id="agent-file"
          type="file"
          accept=".pdf,.xlsx,.csv,.docx,.md,.txt,.json"
          className="hidden"
          onChange={(e) => onFileChange(e.target.files?.[0] || null)}
        />

        <div className="flex-1 min-w-0">
          {file ? (
            <span className="text-sm text-slate-200 flex items-center gap-2">
              <span className="truncate">{file.name}</span>
              <button
                type="button"
                onClick={() => {
                  onFileChange(null);
                  if (inputRef.current) inputRef.current.value = "";
                }}
                className="text-slate-500 hover:text-slate-300"
                aria-label="Remove file"
              >
                <X size={14} />
              </button>
            </span>
          ) : (
            <span className="text-sm text-slate-500">Upload a PDF, XLSX, CSV, DOCX, MD, TXT, or JSON file</span>
          )}
        </div>

        <button
          type="submit"
          disabled={uploading || !file}
          className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-500 text-slate-900 font-semibold hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {uploading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          {uploading ? "Analyzing" : "Analyze"}
        </button>
      </div>
    </form>
  );
}

function ReviewPanel({
  review,
  feedback,
  onFeedbackChange,
  onApprove,
  onReject,
  acting,
}: {
  review: Review;
  feedback: string;
  onFeedbackChange: (value: string) => void;
  onApprove: () => void;
  onReject: () => void;
  acting: boolean;
}) {
  const needsReview = review.findings.filter((f) => f.requiresHumanReview);

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5 space-y-5">
      <p className="text-slate-200 text-sm leading-relaxed">{buildReviewMessage(review)}</p>

      {review.metrics.length > 0 && <MetricsTable metrics={review.metrics} />}

      {needsReview.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Items to review</p>
          {needsReview.map((finding, index) => (
            <FindingCard key={`${finding.code}-${index}`} finding={finding} />
          ))}
        </div>
      )}

      {review.diagnostics?.warnings && review.diagnostics.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-400">Extraction warnings</p>
          <ul className="mt-2 space-y-1 text-sm text-amber-100/80">
            {review.diagnostics.warnings.map((warning, index) => (
              <li key={index}>&bull; {warning}</li>
            ))}
          </ul>
        </div>
      )}

      <textarea
        value={feedback}
        onChange={(e) => onFeedbackChange(e.target.value)}
        placeholder="Add feedback or corrections…"
        rows={3}
        className="w-full rounded-lg border border-slate-700 bg-slate-900/50 p-3 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-cyan-400"
      />

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onReject}
          disabled={acting}
          className="flex-1 py-2.5 px-4 rounded-lg border border-rose-500/50 text-rose-400 font-semibold hover:bg-rose-500/10 disabled:opacity-50 transition-colors"
        >
          Reject
        </button>
        <button
          type="button"
          onClick={onApprove}
          disabled={acting}
          className="flex-1 py-2.5 px-4 rounded-lg bg-emerald-500 text-slate-900 font-semibold hover:bg-emerald-400 disabled:opacity-50 transition-colors"
        >
          Approve
        </button>
      </div>
    </div>
  );
}

function SummaryPanel({ review, onRestart }: { review: Review; onRestart: () => void }) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5 space-y-5">
      <p className="text-slate-200 text-sm leading-relaxed">{buildSummaryMessage(review)}</p>

      {review.metrics.length > 0 && <MetricsTable metrics={review.metrics} />}

      {review.findings.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">All findings</p>
          {review.findings.map((finding, index) => (
            <FindingCard key={`${finding.code}-${index}`} finding={finding} />
          ))}
        </div>
      )}

      {review.diagnostics?.warnings && review.diagnostics.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-400">Extraction warnings</p>
          <ul className="mt-2 space-y-1 text-sm text-amber-100/80">
            {review.diagnostics.warnings.map((warning, index) => (
              <li key={index}>&bull; {warning}</li>
            ))}
          </ul>
        </div>
      )}

      {review.humanFeedback && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Reviewer feedback</p>
          <p className="text-sm text-slate-300 mt-1">{review.humanFeedback}</p>
        </div>
      )}

      <button
        type="button"
        onClick={onRestart}
        className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-700 text-slate-300 hover:text-slate-100 hover:border-slate-500 transition-colors"
      >
        <RotateCcw size={14} />
        Start another review
      </button>
    </div>
  );
}

function ErrorPanel({ error, onRestart }: { error: string; onRestart: () => void }) {
  return (
    <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5">
      <p className="font-semibold text-rose-200">Something went wrong</p>
      <p className="text-sm text-rose-100/80 mt-1">{error}</p>
      <button
        type="button"
        onClick={onRestart}
        className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg border border-rose-500/50 text-rose-400 hover:bg-rose-500/10 transition-colors"
      >
        <RotateCcw size={14} />
        Start over
      </button>
    </div>
  );
}

function MetricsTable({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="rounded-xl border border-slate-700 overflow-hidden">
      <table className="w-full text-sm text-left">
        <thead className="bg-slate-900/50 text-slate-400">
          <tr>
            <th className="px-3 py-2 font-medium">Metric</th>
            <th className="px-3 py-2 font-medium">Raw</th>
            <th className="px-3 py-2 font-medium">Normalized</th>
            <th className="px-3 py-2 font-medium">Confidence</th>
            <th className="px-3 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {metrics.map((metric) => (
            <tr key={metric.key + (metric.period || "")} className="bg-slate-800/30">
              <td className="px-3 py-2 text-slate-200">
                {metric.label}
                {metric.period ? (
                  <span className="block text-xs text-slate-500">{metric.period}</span>
                ) : null}
              </td>
              <td className="px-3 py-2 text-slate-400 font-mono">{metric.raw || "—"}</td>
              <td className="px-3 py-2 text-slate-200 font-medium">{formatMetric(metric.value, metric.unit)}</td>
              <td className="px-3 py-2 text-slate-400">{Math.round(metric.confidence * 100)}%</td>
              <td className="px-3 py-2">
                <StatusBadge status={metric.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }: { status: string | null | undefined }) {
  const color =
    status === "verified"
      ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
      : status === "inferred"
      ? "text-amber-400 bg-amber-400/10 border-amber-400/20"
      : "text-rose-400 bg-rose-400/10 border-rose-400/20";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider border ${color}`}>
      {status || "flagged"}
    </span>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <div className="p-3 rounded-lg border border-slate-700 bg-slate-900/50">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-slate-200">{finding.title}</p>
        <SeverityBadge severity={finding.severity} />
      </div>
      <p className="text-sm text-slate-400 mt-1">{finding.explanation}</p>
      {finding.recommendation && (
        <p className="text-sm text-slate-300 mt-2">
          <span className="font-semibold">Fix:</span> {finding.recommendation}
        </p>
      )}
      {finding.evidence.length > 0 && (
        <div className="mt-2 space-y-1">
          {finding.evidence.map((evidence, index) => (
            <p key={index} className="text-xs text-slate-500">
              {evidence.source}
              {evidence.page ? `, page ${evidence.page}` : ""}
              {evidence.sheet ? `, sheet ${evidence.sheet}` : ""}
              {evidence.cellRange ? `, ${evidence.cellRange}` : ""}
              {evidence.text ? `: ${evidence.text}` : ""}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const color =
    severity === "critical" || severity === "high"
      ? "text-rose-400 bg-rose-400/10 border-rose-400/20"
      : severity === "medium"
      ? "text-amber-400 bg-amber-400/10 border-amber-400/20"
      : "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider border ${color}`}>
      {severity}
    </span>
  );
}
