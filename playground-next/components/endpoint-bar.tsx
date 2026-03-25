"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function EndpointBar({
  url,
  onUrlChange,
  onSend,
  sending,
  className,
}: {
  url: string;
  onUrlChange: (v: string) => void;
  onSend: () => void;
  sending: boolean;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef<number | null>(null);

  const copy = () => {
    try {
      void navigator.clipboard.writeText(url);
    } catch {
      // ignore clipboard errors
    }
    setCopied(true);
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = window.setTimeout(() => setCopied(false), 1500);
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div
      className={cn(
        "flex shrink-0 items-center gap-3 border-b border-border bg-inherit px-4 py-3",
        className
      )}
    >
      <Badge variant="post" className="font-mono text-xs">
        POST
      </Badge>
      <Input
        value={url}
        onChange={(e) => onUrlChange(e.target.value)}
        placeholder="http://localhost:8000/v1/evaluate"
        className="h-9 flex-1 font-mono text-sm"
      />
      <Button
        size="sm"
        onClick={onSend}
        disabled={sending}
        className="gap-1.5"
      >
        <Send className="h-4 w-4" />
        {sending ? "Sending…" : "Send request"}
      </Button>
      <button
        type="button"
        onClick={copy}
        className="flex items-center gap-1 rounded-md border border-border bg-card/80 px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground"
        title={copied ? "Copied" : "Copy URL"}
        aria-label={copied ? "Copied" : "Copy URL"}
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-emerald-400" />
        ) : (
          <Copy className="h-3.5 w-3.5" />
        )}
        <span>{copied ? "Copied" : "Copy"}</span>
      </button>
    </div>
  );
}
