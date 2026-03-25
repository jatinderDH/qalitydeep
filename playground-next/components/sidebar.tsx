"use client";

import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const endpoints = [
  {
    section: "Metrics",
    items: [
      { method: "GET", name: "List Metrics" },
      { method: "POST", name: "Create Metrics" },
      { method: "PUT", name: "Update Metrics" },
      { method: "POST", name: "Batch Create" },
    ],
  },
  {
    section: "Metric Collections",
    items: [
      { method: "GET", name: "List Metric Collections" },
      { method: "POST", name: "Add Collection" },
      { method: "PUT", name: "Update Collection" },
    ],
  },
  {
    section: "Datasets",
    items: [
      { method: "GET", name: "List Datasets" },
      { method: "GET", name: "Pull Dataset" },
      { method: "POST", name: "Push Dataset" },
      { method: "DEL", name: "Delete Dataset" },
    ],
  },
  {
    section: "Evaluation",
    items: [
      { method: "POST", name: "Run LLM Evals" },
    ],
  },
] as const;

const methodVariant = {
  GET: "get",
  POST: "post",
  PUT: "put",
  DEL: "del",
} as const;

export function Sidebar() {
  const visibleGroups = endpoints.filter((group) => group.section === "Evaluation");

  return (
    <aside className="flex h-full min-h-0 w-[260px] shrink-0 flex-col overflow-hidden border-r border-border bg-card">
      <div className="shrink-0 p-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search for endpoints..."
            className="h-8 pl-8 text-sm"
          />
        </div>
      </div>
      <nav className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2 pb-6">
        <div className="py-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Evaluation
        </div>
        {visibleGroups.map((group) => (
          <div key={group.section} className="mt-4">
            <div className="mb-2 px-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {group.section}
            </div>
            <ul className="space-y-0.5">
              {group.items.map((item, i) => (
                <li key={`${group.section}-${i}`}>
                  <button
                    type="button"
                    className={cn(
                      "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors",
                      item.name === "Run LLM Evals"
                        ? "bg-muted text-foreground"
                        : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                    )}
                  >
                    <Badge
                      variant={methodVariant[item.method] ?? "default"}
                      className="shrink-0 font-mono text-[10px]"
                    >
                      {item.method}
                    </Badge>
                    <span className="truncate">{item.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <div className="shrink-0 border-t border-border p-3 text-center text-xs text-muted-foreground">
        Powered by RegalAI
      </div>
    </aside>
  );
}
