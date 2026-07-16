"use client";

import { useState } from "react";
import {
  AlertCircle,
  Brain,
  Check,
  ChevronDown,
  ChevronRight,
  Database,
  Loader2,
  Play,
  RotateCcw,
  Terminal,
  X,
} from "lucide-react";

type AgentState = "running" | "review" | "completed";

type ToolCall = {
  tool: string;
  args: Record<string, unknown>;
  status: "loading" | "success" | "error";
};

const REASONING_STEPS = [
  "Parsed uploaded document and extracted 19 line-level blocks.",
  "Identified income-statement, balance-sheet, and retained-earnings pages.",
  "Matched metric labels to the closest number per line and page.",
  "Detected balance-sheet integrity: assets = liabilities + equity.",
  "Planned tool calls: extract_metrics, add_derived_metrics, run_numeric_rules.",
];

const PLANNED_TOOLS = [
  { tool: "extract_metrics", summary: "Pull revenue, cogs, gross profit, net income, assets, liabilities, equity" },
  { tool: "add_derived_metrics", summary: "Compute gross margin, net margin, current ratio, debt/equity" },
  { tool: "run_numeric_rules", summary: "Check balance-sheet balance and gross-profit consistency" },
];

const SAMPLE_TOOL: ToolCall = {
  tool: "run_numeric_rules",
  args: {
    total_assets: 13060,
    total_liabilities: 8895,
    equity: 4165,
    revenue: 6875,
    cogs: 4125,
    gross_profit: 2750,
  },
  status: "success",
};

const PROPOSED_ACTION = {
  title: "Submit review result",
  body: `Status: completed
Findings: none
Confidence: 96% extraction
Balance sheet check: 13,060 = 8,895 + 4,165 ✓
Gross profit check: 2,750 = 6,875 - 4,125 ✓`,
};

export function AgentOrchestrator() {
  const [state, setState] = useState<AgentState>("running");
  const [reasoningOpen, setReasoningOpen] = useState(true);
  const [feedback, setFeedback] = useState("");
  const [toolStatus, setToolStatus] = useState<ToolCall["status"]>("loading");
  const [lastDecision, setLastDecision] = useState<"approved" | "rejected" | null>(null);

  function setDemoState(next: AgentState) {
    setState(next);
    setLastDecision(null);
    if (next === "running") {
      setToolStatus("loading");
    } else if (next === "completed") {
      setToolStatus("success");
    } else if (next === "review") {
      setToolStatus("success");
    }
  }

  const stateButton = (value: AgentState, label: string) => (
    <button
      key={value}
      type="button"
      onClick={() => setDemoState(value)}
      className={`px-3 py-1.5 text-xs font-semibold rounded-full border transition-colors ${
        state === value
          ? "bg-lime-400 text-slate-900 border-lime-400"
          : "bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-500"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 md:p-10 font-sans">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Agent Orchestration</h1>
            <p className="text-slate-400 text-sm mt-1">
              Human-in-the-loop review flow with verifiable tool calls and source evidence.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {stateButton("running", "Running")}
            {stateButton("review", "Awaiting Review")}
            {stateButton("completed", "Completed")}
            <button
              type="button"
              onClick={() => setDemoState("running")}
              className="ml-2 p-1.5 rounded-full border border-slate-700 text-slate-400 hover:text-slate-100 hover:border-slate-500"
              aria-label="Restart demo"
            >
              <RotateCcw size={16} />
            </button>
          </div>
        </header>

        {/* Main split view */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Timeline */}
          <aside className="lg:col-span-4 space-y-3">
            <TimelineStep
              icon={<Brain size={18} />}
              label="Reasoning & Plan"
              status={state === "running" ? "active" : "done"}
              isActive={state === "running"}
            />
            <TimelineStep
              icon={<Terminal size={18} />}
              label="Tool Execution"
              status={state === "running" ? "active" : state === "review" ? "done" : "done"}
              isActive={state === "running"}
            />
            <TimelineStep
              icon={<AlertCircle size={18} />}
              label="Human Review Gate"
              status={state === "review" ? "active" : state === "completed" ? "done" : "pending"}
              isActive={state === "review"}
            />
            <TimelineStep
              icon={<Check size={18} />}
              label="Completed"
              status={state === "completed" ? "active" : "pending"}
              isActive={state === "completed"}
            />

            <div className="mt-6 p-4 rounded-lg border border-slate-700 bg-slate-800/50">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                System status
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Parser</span>
                  <span className="font-mono text-lime-400">pymupdf</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Rule version</span>
                  <span className="font-mono">financial-core/1.0.0</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Confidence</span>
                  <span className="font-mono">96%</span>
                </div>
              </div>
            </div>
          </aside>

          {/* Active step detail */}
          <section className="lg:col-span-8">
            {state === "running" && (
              <div className="space-y-6">
                <ReasoningCard open={reasoningOpen} onToggle={() => setReasoningOpen((v) => !v)} />
                <ToolCallCard tool={SAMPLE_TOOL} status={toolStatus} />
              </div>
            )}

            {state === "review" && (
              <HumanReviewGate
                feedback={feedback}
                onFeedbackChange={setFeedback}
                onApprove={() => {
                  setLastDecision("approved");
                  setState("completed");
                }}
                onReject={() => {
                  setLastDecision("rejected");
                  setState("running");
                }}
              />
            )}

            {state === "completed" && (
              <CompletedCard
                decision={lastDecision}
                onRestart={() => setDemoState("running")}
              />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function TimelineStep({
  icon,
  label,
  status,
  isActive,
}: {
  icon: React.ReactNode;
  label: string;
  status: "pending" | "active" | "done";
  isActive: boolean;
}) {
  const color =
    status === "done"
      ? "border-lime-400/30 bg-lime-400/10 text-lime-400"
      : status === "active"
        ? "border-cyan-400/50 bg-cyan-400/10 text-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.15)]"
        : "border-slate-700 bg-slate-800/40 text-slate-500";

  return (
    <div className={`flex items-center gap-4 p-4 rounded-xl border ${color} transition-all`}>
      <div className="shrink-0">{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold">{label}</p>
        <p className="text-xs text-slate-400">
          {status === "active" && "In progress…"}
          {status === "done" && "Finished"}
          {status === "pending" && "Waiting"}
        </p>
      </div>
      {isActive && <Loader2 size={16} className="animate-spin text-cyan-400" />}
      {status === "done" && <Check size={16} className="text-lime-400" />}
    </div>
  );
}

function ReasoningCard({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/50 overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-slate-800/80 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Brain size={20} className="text-cyan-400 animate-pulse" />
          <div>
            <h2 className="font-semibold">Reasoning & Plan</h2>
            <p className="text-xs text-slate-400">Confidence score: 94%</p>
          </div>
        </div>
        {open ? <ChevronDown size={18} className="text-slate-400" /> : <ChevronRight size={18} className="text-slate-400" />}
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 border-t border-slate-700/50">
          <div className="pt-4 space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Chain-of-thought
            </h3>
            <ul className="space-y-2">
              {REASONING_STEPS.map((step, idx) => (
                <li key={idx} className="flex gap-3 text-sm text-slate-300">
                  <span className="shrink-0 w-5 h-5 rounded-full bg-slate-700 text-[10px] flex items-center justify-center text-slate-300">
                    {idx + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Planned tool calls
            </h3>
            <div className="grid gap-2">
              {PLANNED_TOOLS.map((tool) => (
                <div
                  key={tool.tool}
                  className="flex items-center gap-3 p-3 rounded-lg border border-slate-700 bg-slate-900/50"
                >
                  <div className="p-1.5 rounded bg-slate-700 text-slate-300">
                    <Database size={14} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-mono font-medium text-cyan-300">{tool.tool}</p>
                    <p className="text-xs text-slate-400 truncate">{tool.summary}</p>
                  </div>
                  <Play size={14} className="text-slate-500" />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ToolCallCard({ tool, status }: { tool: ToolCall; status: ToolCall["status"] }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-slate-800 text-cyan-400">
            <Terminal size={18} />
          </div>
          <div>
            <h2 className="font-semibold">Tool call</h2>
            <p className="text-xs text-slate-400 font-mono">{tool.tool}</p>
          </div>
        </div>
        <span
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
            status === "loading"
              ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
              : status === "success"
                ? "border-lime-400/30 bg-lime-400/10 text-lime-400"
                : "border-rose-500/30 bg-rose-500/10 text-rose-400"
          }`}
        >
          {status === "loading" && <Loader2 size={12} className="animate-spin" />}
          {status === "success" && <Check size={12} />}
          {status === "error" && <X size={12} />}
          {status}
        </span>
      </div>

      <div className="rounded-lg bg-slate-950 border border-slate-800 p-4 overflow-auto">
        <pre className="text-xs font-mono text-slate-300">
          <code>{JSON.stringify(tool.args, null, 2)}</code>
        </pre>
      </div>

      <p className="text-xs text-slate-400">
        The tool result is verified against the original document evidence before the next step is
        scheduled.
      </p>
    </div>
  );
}

function HumanReviewGate({
  feedback,
  onFeedbackChange,
  onApprove,
  onReject,
}: {
  feedback: string;
  onFeedbackChange: (value: string) => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div className="rounded-xl border border-amber-500/30 bg-slate-800/50 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertCircle size={22} className="text-amber-400" />
          <h2 className="text-lg font-semibold">Human review required</h2>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border border-amber-500/40 bg-amber-500/10 text-amber-400">
          Awaiting Human Approval
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Proposed action
          </h3>
          <p className="text-sm font-medium mb-3">{PROPOSED_ACTION.title}</p>
          <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap">
            {PROPOSED_ACTION.body}
          </pre>
        </div>

        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Evidence preview
          </h3>
          <ul className="space-y-2 text-sm text-slate-300">
            <li className="flex gap-2">
              <Check size={14} className="text-lime-400 mt-1" />
              Extracted block L15: <span className="font-mono">Net income $945</span>
            </li>
            <li className="flex gap-2">
              <Check size={14} className="text-lime-400 mt-1" />
              Source page 2: <span className="font-mono">Gross profit $2,750</span>
            </li>
            <li className="flex gap-2">
              <Check size={14} className="text-lime-400 mt-1" />
              Balance sheet: <span className="font-mono">13,060 = 8,895 + 4,165</span>
            </li>
          </ul>
        </div>
      </div>

      <div>
        <label htmlFor="reviewer-feedback" className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          Human feedback / corrections
        </label>
        <textarea
          id="reviewer-feedback"
          value={feedback}
          onChange={(e) => onFeedbackChange(e.target.value)}
          placeholder="Add a correction, ask for a re-run, or explain why this should be rejected..."
          className="w-full h-28 rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500"
        />
      </div>

      <div className="flex items-center gap-3 justify-end">
        <button
          type="button"
          onClick={onReject}
          className="px-4 py-2 rounded-lg border border-rose-500/40 bg-rose-500/10 text-rose-400 text-sm font-semibold hover:bg-rose-500/20 transition-colors"
        >
          Reject & Redirect
        </button>
        <button
          type="button"
          onClick={onApprove}
          className="px-4 py-2 rounded-lg border border-lime-400/40 bg-lime-400/10 text-lime-400 text-sm font-semibold hover:bg-lime-400/20 transition-colors"
        >
          Approve & Execute
        </button>
      </div>
    </div>
  );
}

function CompletedCard({
  decision,
  onRestart,
}: {
  decision: "approved" | "rejected" | null;
  onRestart: () => void;
}) {
  return (
    <div className="rounded-xl border border-lime-400/30 bg-slate-800/50 p-8 text-center space-y-4">
      <div className="inline-flex p-4 rounded-full bg-lime-400/10 text-lime-400">
        <Check size={32} />
      </div>
      <h2 className="text-2xl font-semibold">Review completed</h2>
      <p className="text-slate-400 max-w-lg mx-auto">
        All planned tool calls executed successfully, numeric checks passed, and the review result
        {decision ? ` was ${decision}` : " is ready"}.
      </p>
      <div className="flex justify-center gap-3 pt-2">
        <button
          type="button"
          onClick={onRestart}
          className="px-4 py-2 rounded-lg border border-slate-700 text-slate-300 text-sm font-semibold hover:bg-slate-800 transition-colors"
        >
          Run another
        </button>
        <button
          type="button"
          className="px-4 py-2 rounded-lg border border-lime-400/40 bg-lime-400/10 text-lime-400 text-sm font-semibold hover:bg-lime-400/20 transition-colors"
        >
          Export report
        </button>
      </div>
    </div>
  );
}
