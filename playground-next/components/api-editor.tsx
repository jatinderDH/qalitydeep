"use client";

import { X, ChevronDown, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const DEFAULT_INPUT = "How tall is mount everest?";
const DEFAULT_OUTPUT = "No clue, pretty tall I guess?";

export type RequestPayload = {
  metricCollection: string;
  llmTestCases: Array<{ input: string; actualOutput: string }>;
};

export function ApiEditor({
  apiKey,
  setApiKey,
  metricCollection,
  setMetricCollection,
  cases,
  setCases,
}: {
  apiKey: string;
  setApiKey: (v: string) => void;
  metricCollection: string;
  setMetricCollection: (v: string) => void;
  cases: Array<{ input: string; actualOutput: string }>;
  setCases: React.Dispatch<React.SetStateAction<Array<{ input: string; actualOutput: string }>>>;
}) {

  const addCase = () => setCases((c) => [...c, { input: "", actualOutput: "" }]);

  const removeCase = (i: number) => {
    if (cases.length <= 1) return;
    setCases((c) => c.filter((_, j) => j !== i));
  };

  const updateCase = (i: number, field: "input" | "actualOutput", value: string) => {
    setCases((c) => {
      const next = [...c];
      next[i] = { ...next[i], [field]: value };
      return next;
    });
  };

  return (
    <div className="flex flex-col p-6">
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2 text-sm font-medium">Headers</div>
        </CardHeader>
        <CardContent className="max-h-[220px] overflow-y-auto overflow-x-hidden space-y-2">
          <div className="flex items-center gap-2">
            <label className="min-w-[140px] text-sm text-muted-foreground">
              QAlity_API_Key
            </label>
            <span className="text-xs text-red-400">Required</span>
          </div>
          <div className="relative">
            <Input
              type="password"
              placeholder="<API-KEY>"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="pr-8 font-mono text-sm"
            />
            <button
              type="button"
              onClick={() => setApiKey("")}
              className={cn(
                "absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground",
                apiKey ? "opacity-100" : "pointer-events-none opacity-0"
              )}
              aria-label="Clear API key"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader className="pb-3">
          <div className="text-sm font-medium">Body parameters</div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="mb-1.5 flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">metricCollection</span>
              <span className="text-xs text-red-400">Required</span>
            </div>
            <div className="relative">
              <Input
                value={metricCollection}
                onChange={(e) => setMetricCollection(e.target.value)}
                placeholder="Collection Name"
                className="pr-8"
              />
              <button
                type="button"
                onClick={() => setMetricCollection("")}
                className={cn(
                  "absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground",
                  metricCollection ? "opacity-100" : "pointer-events-none opacity-0"
                )}
                aria-label="Clear metric collection"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                llmTestCases <span className="text-muted-foreground/80">(list of objects)</span>
              </span>
              <Button variant="ghost" size="sm" onClick={addCase} className="h-7 gap-1 text-xs">
                <Plus className="h-3.5 w-3.5" />
                Add item
              </Button>
            </div>
            <div className="space-y-3">
              {cases.map((c, i) => (
                <Card key={i} className="border-muted/50">
                  <CardContent className="p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground">
                        Item {i + 1}
                      </span>
                      {cases.length > 1 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 text-muted-foreground hover:text-foreground"
                          onClick={() => removeCase(i)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                    <div className="space-y-2">
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">
                          input <span className="text-red-400">*</span>
                        </label>
                        <div className="relative">
                          <Input
                            value={c.input}
                            onChange={(e) => updateCase(i, "input", e.target.value)}
                            placeholder={DEFAULT_INPUT}
                            className="pr-8 text-sm"
                          />
                          <button
                            type="button"
                            onClick={() => updateCase(i, "input", "")}
                            className={cn(
                              "absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground",
                              c.input ? "opacity-100" : "pointer-events-none opacity-0"
                            )}
                            aria-label="Clear input"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">
                          actualOutput <span className="text-red-400">*</span>
                        </label>
                        <div className="relative">
                          <Input
                            value={c.actualOutput}
                            onChange={(e) => updateCase(i, "actualOutput", e.target.value)}
                            placeholder={DEFAULT_OUTPUT}
                            className="pr-8 text-sm"
                          />
                          <button
                            type="button"
                            onClick={() => updateCase(i, "actualOutput", "")}
                            className={cn(
                              "absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground",
                              c.actualOutput
                                ? "opacity-100"
                                : "pointer-events-none opacity-0"
                            )}
                            aria-label="Clear actual output"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            <button
              type="button"
              className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              <ChevronDown className="h-3.5 w-3.5" />
              6 more optional properties name, expectedOutput, retrievalContext…
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
