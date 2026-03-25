"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, Copy, Maximize2, X } from "lucide-react";
import Prism from "prismjs";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-json";
import "prismjs/components/prism-python";
import "prismjs/components/prism-typescript";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { EvalResponseView } from "@/components/eval-response-view";

const curlExample = `curl -X POST http://localhost:8000/v1/evaluate \\
  -H "Content-Type: application/json" \\
  -H "QAlity_API_Key: <QALITY-API-KEY>" \\
  -d '{
  "metricCollection": "Collection Name",
  "llmTestCases": [
    {
      "input": "How tall is mount everest?",
      "actualOutput": "No clue, pretty tall I guess?"
    }
  ]
}'`;

const baseTsExample = `const response = await fetch("http://localhost:8000/v1/evaluate", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "QAlity_API_Key": "<QALITY-API-KEY>",
  },
  body: JSON.stringify({
    metricCollection: "Collection Name",
    llmTestCases: [{ input: "How tall is mount everest?", actualOutput: "No clue, pretty tall I guess?" }]
  })
});
const data = await response.json();`;

const basePyExample = `import requests

response = requests.post(
    "http://localhost:8000/v1/evaluate",
    headers={
        "Content-Type": "application/json",
        "QAlity_API_Key": "<QALITY-API-KEY>",
    },
    json={
        "metricCollection": "Collection Name",
        "llmTestCases": [{"input": "How tall is mount everest?", "actualOutput": "No clue, pretty tall I guess?"}]
    }
)
data = response.json()`;

const responseExample = `{
  "success": false,
  "error": "Invalid API key",
  "deprecated": false
}`;

function CodeBlock({
  code,
  language,
  className,
  actions,
}: {
  code: string;
  language?: "bash" | "typescript" | "python" | "json";
  className?: string;
  actions?: React.ReactNode;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const highlighted = mounted
    ? (() => {
        if (!language) return null;
        const grammar = (Prism.languages as Record<string, Prism.Grammar | undefined>)[language];
        if (!grammar) return null;
        return Prism.highlight(code, grammar, language);
      })()
    : null;

  return (
    <div className="relative">
      {actions ? <div className="absolute right-2 top-2 z-10 flex gap-1">{actions}</div> : null}
      <pre
        className={cn(
          "overflow-auto rounded-lg border border-border bg-muted/30 p-3 pr-12 font-mono text-xs leading-relaxed text-foreground",
          className
        )}
      >
        <div className="flex">
          <div className="select-none pr-4 text-right text-[10px] leading-relaxed text-muted-foreground/80">
            {(code.split("\n") || []).map((_, index) => (
              <div key={index}>{index + 1}</div>
            ))}
          </div>
          <code className={cn("flex-1", language ? `language-${language}` : undefined)}>
            {(highlighted ? highlighted.split("\n") : code.split("\n")).map(
              (line, index) => (
                <span
                  key={index}
                  className="block whitespace-pre"
                  dangerouslySetInnerHTML={
                    highlighted ? { __html: line || " " } : undefined
                  }
                >
                  {!highlighted ? line || " " : null}
                </span>
              )
            )}
          </code>
        </div>
      </pre>
    </div>
  );
}

function IconButton({
  title,
  onClick,
  children,
}: {
  title: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md border border-border bg-card/70 p-1.5 text-muted-foreground backdrop-blur hover:bg-muted hover:text-foreground"
      title={title}
      aria-label={title}
    >
      {children}
    </button>
  );
}

function ExpandModal({
  open,
  title,
  code,
  language,
  onClose,
}: {
  open: boolean;
  title: string;
  code: string;
  language?: "bash" | "typescript" | "python" | "json";
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6">
      <div className="flex h-full w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl">
        <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
          <div className="text-sm font-semibold">{title}</div>
          <div className="flex gap-2">
            <IconButton title="Copy" onClick={() => navigator.clipboard.writeText(code)}>
              <Copy className="h-4 w-4" />
            </IconButton>
            <IconButton title="Close" onClick={onClose}>
              <X className="h-4 w-4" />
            </IconButton>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-4">
          <CodeBlock code={code} language={language} className="min-h-[70vh]" />
        </div>
      </div>
    </div>
  );
}

export function CodeBlockPanel({
  requestPayload,
  apiKey,
  response,
}: {
  requestPayload: { metricCollection: string; llmTestCases: Array<{ input: string; actualOutput: string }> };
  apiKey: string;
  response: { status: number; elapsed: number; size: number; data: unknown } | null;
}) {
  const [activeTab, setActiveTab] = useState("curl");
  const [expanded, setExpanded] = useState<{
    open: boolean;
    title: string;
    code: string;
    language?: "bash" | "typescript" | "python" | "json";
  }>({ open: false, title: "", code: "" });
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const copyTimeoutRef = useRef<number | null>(null);

  const handleCopy = useCallback((key: string, text: string) => {
    try {
      void navigator.clipboard.writeText(text);
    } catch {
      // ignore clipboard errors
    }
    setCopiedKey(key);
    if (copyTimeoutRef.current) {
      window.clearTimeout(copyTimeoutRef.current);
    }
    copyTimeoutRef.current = window.setTimeout(() => setCopiedKey(null), 1500);
  }, []);

  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        window.clearTimeout(copyTimeoutRef.current);
      }
    };
  }, []);

  const effectiveApiKey = apiKey || "<QALITY-API-KEY>";

  const tsExample = useMemo(
    () =>
      baseTsExample.replace(
        '"QAlity_API_Key": "<QALITY-API-KEY>"',
        `"QAlity_API_Key": "${effectiveApiKey}"`
      ),
    [effectiveApiKey]
  );

  const pyExample = useMemo(
    () =>
      basePyExample.replace(
        '"QAlity_API_Key": "<QALITY-API-KEY>"',
        `"QAlity_API_Key": "${effectiveApiKey}"`
      ),
    [effectiveApiKey]
  );

  const curlCode =
    requestPayload?.llmTestCases?.length > 0
      ? `curl -X POST http://localhost:8000/v1/evaluate \\
  -H "Content-Type: application/json" \\
  -H "QAlity_API_Key: ${effectiveApiKey}" \\
  -d '${JSON.stringify(
          {
            metricCollection: requestPayload.metricCollection,
            llmTestCases: requestPayload.llmTestCases,
          },
          null,
          2
        ).replace(/'/g, "'\\''")}'`
      : curlExample;

  const requestCode = useMemo(() => {
    if (activeTab === "ts") return tsExample;
    if (activeTab === "py") return pyExample;
    return curlCode;
  }, [activeTab, curlCode]);

  const requestLang = useMemo((): "bash" | "typescript" | "python" => {
    if (activeTab === "ts") return "typescript";
    if (activeTab === "py") return "python";
    return "bash";
  }, [activeTab]);

  const responseCode = useMemo(() => {
    if (!response) return responseExample;
    return typeof response.data === "object" ? JSON.stringify(response.data, null, 2) : String(response.data);
  }, [response]);

  return (
    <div className="flex flex-col gap-6 px-4 py-3">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="space-y-3 border-b border-border pb-3">
          <h3 className="text-sm font-semibold">REQUEST</h3>
          <TabsList className="h-8 w-full justify-start rounded-lg bg-muted/50 p-0.5">
            <TabsTrigger value="curl" className="rounded-md px-3 text-xs">
              cURL
            </TabsTrigger>
            <TabsTrigger value="ts" className="rounded-md px-3 text-xs">
              TypeScript
            </TabsTrigger>
            <TabsTrigger value="py" className="rounded-md px-3 text-xs">
              Python
            </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="curl" className="mt-3 data-[state=inactive]:hidden">
          <CodeBlock
            code={curlCode}
            language="bash"
            className="min-h-[120px]"
            actions={
              <>
                {copiedKey === "request-curl" && (
                  <span className="mr-1 text-[10px] font-medium text-emerald-400">Copied</span>
                )}
                <IconButton
                  title="Expand"
                  onClick={() =>
                    setExpanded({
                      open: true,
                      title: "REQUEST – cURL",
                      code: curlCode,
                      language: "bash",
                    })
                  }
                >
                  <Maximize2 className="h-4 w-4" />
                </IconButton>
                <IconButton
                  title={copiedKey === "request-curl" ? "Copied" : "Copy"}
                  onClick={() => handleCopy("request-curl", curlCode)}
                >
                  {copiedKey === "request-curl" ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </IconButton>
              </>
            }
          />
        </TabsContent>
        <TabsContent value="ts" className="mt-3 data-[state=inactive]:hidden">
          <CodeBlock
            code={tsExample}
            language="typescript"
            className="min-h-[120px]"
            actions={
              <>
                {copiedKey === "request-ts" && (
                  <span className="mr-1 text-[10px] font-medium text-emerald-400">Copied</span>
                )}
                <IconButton
                  title="Expand"
                  onClick={() =>
                    setExpanded({
                      open: true,
                      title: "REQUEST – TypeScript",
                      code: tsExample,
                      language: "typescript",
                    })
                  }
                >
                  <Maximize2 className="h-4 w-4" />
                </IconButton>
                <IconButton
                  title={copiedKey === "request-ts" ? "Copied" : "Copy"}
                  onClick={() => handleCopy("request-ts", tsExample)}
                >
                  {copiedKey === "request-ts" ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </IconButton>
              </>
            }
          />
        </TabsContent>
        <TabsContent value="py" className="mt-3 data-[state=inactive]:hidden">
          <CodeBlock
            code={pyExample}
            language="python"
            className="min-h-[120px]"
            actions={
              <>
                {copiedKey === "request-py" && (
                  <span className="mr-1 text-[10px] font-medium text-emerald-400">Copied</span>
                )}
                <IconButton
                  title="Expand"
                  onClick={() =>
                    setExpanded({
                      open: true,
                      title: "REQUEST – Python",
                      code: pyExample,
                      language: "python",
                    })
                  }
                >
                  <Maximize2 className="h-4 w-4" />
                </IconButton>
                <IconButton
                  title={copiedKey === "request-py" ? "Copied" : "Copy"}
                  onClick={() => handleCopy("request-py", pyExample)}
                >
                  {copiedKey === "request-py" ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </IconButton>
              </>
            }
          />
        </TabsContent>
      </Tabs>

      <div>
        <h3 className="mb-3 text-sm font-semibold">RESPONSE</h3>
        {response ? (
          <>
            <div className="mb-4">
              <div className="mb-2 flex flex-wrap gap-4 text-xs">
                <span
                  className={
                    response.status >= 200 && response.status < 300
                      ? "text-emerald-400"
                      : "text-red-400"
                  }
                >
                  status: {response.status}
                </span>
                <span className="text-muted-foreground">time: {response.elapsed}ms</span>
                <span className="text-muted-foreground">size: {response.size}b</span>
              </div>
              <CodeBlock
                code={responseCode}
                language="json"
                className="min-h-[100px]"
                actions={
                  <>
                    {copiedKey === "response" && (
                      <span className="mr-1 text-[10px] font-medium text-emerald-400">Copied</span>
                    )}
                    <IconButton
                      title="Expand"
                      onClick={() =>
                        setExpanded({
                          open: true,
                          title: "RESPONSE",
                          code: responseCode,
                          language: "json",
                        })
                      }
                    >
                      <Maximize2 className="h-4 w-4" />
                    </IconButton>
                    <IconButton
                      title={copiedKey === "response" ? "Copied" : "Copy"}
                      onClick={() => handleCopy("response", responseCode)}
                    >
                      {copiedKey === "response" ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </IconButton>
                  </>
                }
              />
            </div>
            <EvalResponseView
              status={response.status}
              elapsed={response.elapsed}
              size={response.size}
              data={response.data}
              hideRawSection
            />
          </>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="inline-flex h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
              <span>Waiting for response. Click “Send request” to run an evaluation.</span>
            </div>
            <CodeBlock
              code={responseExample}
              language="json"
              className="min-h-[100px] opacity-70"
              actions={
                <>
                  {copiedKey === "response-example" && (
                    <span className="mr-1 text-[10px] font-medium text-emerald-400">
                      Copied
                    </span>
                  )}
                  <IconButton
                    title="Expand"
                    onClick={() =>
                      setExpanded({
                        open: true,
                        title: "RESPONSE",
                        code: responseExample,
                        language: "json",
                      })
                    }
                  >
                    <Maximize2 className="h-4 w-4" />
                  </IconButton>
                  <IconButton
                    title={copiedKey === "response-example" ? "Copied" : "Copy"}
                    onClick={() => handleCopy("response-example", responseExample)}
                  >
                    {copiedKey === "response-example" ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </IconButton>
                </>
              }
            />
          </div>
        )}
      </div>

      <ExpandModal
        open={expanded.open}
        title={expanded.title}
        code={expanded.code}
        language={expanded.language}
        onClose={() => setExpanded((s) => ({ ...s, open: false }))}
      />
    </div>
  );
}
