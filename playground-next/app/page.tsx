"use client";

import { useState, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { Navbar } from "@/components/navbar";
import { Sidebar } from "@/components/sidebar";
import { EndpointBar } from "@/components/endpoint-bar";
import { ApiEditor, type RequestPayload } from "@/components/api-editor";

const CodeBlockPanel = dynamic(
  () => import("@/components/code-block-panel").then((m) => m.CodeBlockPanel),
  { ssr: false }
);

const DEFAULT_URL = "http://localhost:8000/v1/evaluate";
const DEFAULT_INPUT = "How tall is mount everest?";
const DEFAULT_OUTPUT = "No clue, pretty tall I guess?";

export default function DocsPage() {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [apiKey, setApiKey] = useState("");
  const [metricCollection, setMetricCollection] = useState("Collection Name");
  const [cases, setCases] = useState<Array<{ input: string; actualOutput: string }>>([
    { input: DEFAULT_INPUT, actualOutput: DEFAULT_OUTPUT },
  ]);
  const [response, setResponse] = useState<{
    status: number;
    elapsed: number;
    size: number;
    data: unknown;
  } | null>(null);
  const [sending, setSending] = useState(false);

  const payload = useMemo<RequestPayload>(
    () => ({ metricCollection, llmTestCases: cases }),
    [metricCollection, cases]
  );

  const sendRequest = useCallback(async () => {
    setSending(true);
    setResponse(null);
    const start = performance.now();
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiKey ? { QAlity_API_Key: apiKey } : {}),
        },
        body: JSON.stringify(payload),
      });
      const elapsed = Math.round(performance.now() - start);
      const text = await res.text();
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        data = { raw: text };
      }
      setResponse({
        status: res.status,
        elapsed,
        size: new Blob([text]).size,
        data: res.ok ? data : { error: (data as { detail?: string })?.detail ?? text },
      });
    } catch (err) {
      setResponse({
        status: 0,
        elapsed: Math.round(performance.now() - start),
        size: 0,
        data: { error: (err as Error).message },
      });
    } finally {
      setSending(false);
    }
  }, [url, apiKey, payload]);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Navbar />
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Sidebar />

        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <div className="shrink-0 bg-card">
            <EndpointBar
              url={url}
              onUrlChange={setUrl}
              onSend={sendRequest}
              sending={sending}
            />
          </div>

          <div className="min-h-0 min-w-0 flex-1">
            <PanelGroup direction="horizontal" className="h-full w-full min-h-0 min-w-0">
              <Panel defaultSize={50} minSize={35} className="min-h-0 min-w-0">
                <div className="h-full min-h-0 min-w-0 overflow-y-auto">
                  <ApiEditor
                    apiKey={apiKey}
                    setApiKey={setApiKey}
                    metricCollection={metricCollection}
                    setMetricCollection={setMetricCollection}
                    cases={cases}
                    setCases={setCases}
                  />
                </div>
              </Panel>

              <PanelResizeHandle
                hitAreaMargins={{ fine: 10, coarse: 15 }}
                className="w-2 cursor-col-resize shrink-0 bg-border hover:bg-primary/40 data-[panel-resize-handle-state=drag]:bg-primary"
              />

              <Panel defaultSize={50} minSize={30} className="min-h-0 min-w-0 border-l border-border bg-card">
                <div className="h-full min-h-0 overflow-y-auto">
                  <CodeBlockPanel requestPayload={payload} apiKey={apiKey} response={response} />
                </div>
              </Panel>
            </PanelGroup>
          </div>
        </div>
      </div>
    </div>
  );
}
