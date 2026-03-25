"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

type EvalData = {
  success?: boolean;
  results?: Array<{ name?: string; metrics?: Record<string, number>; reasons?: Record<string, string> }>;
  summary?: Record<string, { avg?: number; pass_rate?: number } | number>;
};

export function EvalResponseView({
  status,
  elapsed,
  size,
  data,
  hideRawSection = false,
  rawJson,
  onCopyRaw,
  copied,
  onExpandRaw,
}: {
  status: number;
  elapsed: number;
  size: number;
  data: unknown;
  hideRawSection?: boolean;
  rawJson?: string;
  onCopyRaw?: () => void;
  copied?: boolean;
  onExpandRaw?: () => void;
}) {
  const [rawOpen, setRawOpen] = useState(false);
  const [expandedCase, setExpandedCase] = useState<number | null>(null);

  const evalData = data as EvalData | null;
  const results = evalData?.results ?? [];
  const summary = evalData?.summary ?? {};
  const numCases = typeof summary.num_cases === "number" ? summary.num_cases : results.length;

  const metricSummaryEntries = Object.entries(summary).filter(
    (entry): entry is [string, { avg?: number; pass_rate?: number }] =>
      entry[0] !== "num_cases" &&
      typeof entry[1] === "object" &&
      entry[1] !== null &&
      "avg" in entry[1]
  );

  const isSuccess = status >= 200 && status < 300;

  return (
    <div className="space-y-4">
      {/* Metric cards */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <MetricCard
          label="Status"
          value={String(status)}
          variant={isSuccess ? "success" : "error"}
        />
        <MetricCard label="Time" value={`${elapsed} ms`} />
        <MetricCard label="Size" value={`${size} b`} />
        <MetricCard label="Cases" value={String(numCases)} />
      </div>

      {isSuccess && metricSummaryEntries.length > 0 && (
        <>
          {/* Per-metric avg + pass rate */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {metricSummaryEntries.map(([name, v]) => (
              <MetricCard
                key={name}
                label={name}
                value={typeof v.avg === "number" ? v.avg.toFixed(3) : "—"}
                delta={
                  typeof v.pass_rate === "number"
                    ? `${(v.pass_rate * 100).toFixed(0)}% pass`
                    : undefined
                }
              />
            ))}
          </div>

          {/* Bar chart: metric averages */}
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">Metric averages</div>
            <div className="space-y-1.5">
              {metricSummaryEntries.map(([name, v]) => {
                const avg = typeof v.avg === "number" ? v.avg : 0;
                return (
                  <div key={name} className="flex items-center gap-2">
                    <span className="w-24 shrink-0 text-xs text-muted-foreground">{name}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          avg >= 0.7 ? "bg-emerald-500" : avg >= 0.5 ? "bg-amber-500" : "bg-red-500"
                        )}
                        style={{ width: `${Math.min(100, avg * 100)}%` }}
                      />
                    </div>
                    <span className="w-10 shrink-0 text-right text-xs tabular-nums">{avg.toFixed(2)}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Per-case results */}
          {results.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground">Per-case results</div>
              <div className="space-y-1">
                {results.map((r, i) => {
                  const metrics = r.metrics ?? {};
                  const reasons = r.reasons ?? {};
                  const isExpanded = expandedCase === i;
                  return (
                    <div
                      key={i}
                      className="rounded-md border border-border bg-muted/20 overflow-hidden"
                    >
                      <button
                        type="button"
                        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-muted/30"
                        onClick={() => setExpandedCase(isExpanded ? null : i)}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5 shrink-0" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 shrink-0" />
                        )}
                        <span className="font-medium">
                          {r.name ?? `Case ${i + 1}`}
                        </span>
                        <span className="text-muted-foreground">
                          {Object.entries(metrics)
                            .map(([k, v]) => `${k}: ${typeof v === "number" ? v.toFixed(2) : v}`)
                            .join(" · ")}
                        </span>
                      </button>
                      {isExpanded && Object.keys(reasons).length > 0 && (
                        <div className="border-t border-border bg-muted/10 px-3 py-2 text-xs">
                          {Object.entries(reasons).map(([metric, reason]) => (
                            <div key={metric} className="mb-1.5 last:mb-0">
                              <span className="font-medium text-muted-foreground">{metric}:</span>{" "}
                              {reason}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}

      {!hideRawSection && rawJson != null && (
        <div className="rounded-md border border-border">
          <button
            type="button"
            className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium hover:bg-muted/30"
            onClick={() => setRawOpen(!rawOpen)}
          >
            <span>Raw response</span>
            {rawOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
          {rawOpen && (
            <div className="border-t border-border p-2">
              <pre className="max-h-[240px] overflow-auto rounded bg-muted/30 p-2 font-mono text-[11px]">
                {rawJson}
              </pre>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={onCopyRaw}
                  className="rounded border border-border bg-muted/50 px-2 py-1 text-xs hover:bg-muted"
                >
                  {copied ? "Copied" : "Copy"}
                </button>
                <button
                  type="button"
                  onClick={onExpandRaw}
                  className="rounded border border-border bg-muted/50 px-2 py-1 text-xs hover:bg-muted"
                >
                  Expand
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  delta,
  variant,
}: {
  label: string;
  value: string;
  delta?: string;
  variant?: "success" | "error";
}) {
  return (
    <div className="rounded-md border border-border bg-card p-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div
        className={cn(
          "text-sm font-semibold tabular-nums",
          variant === "success" && "text-emerald-400",
          variant === "error" && "text-red-400"
        )}
      >
        {value}
      </div>
      {delta != null && <div className="text-[10px] text-muted-foreground">{delta}</div>}
    </div>
  );
}
