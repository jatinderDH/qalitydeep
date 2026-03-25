"use client";

import { useState } from "react";
import { Navbar } from "@/components/navbar";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Check, Copy, Mail } from "lucide-react";

const API_BASE = "http://localhost:8000";

export default function CreateApiKeyPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const canSubmit = email.trim().length > 3 && !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    setApiKey(null);
    setUserId(null);

    try {
      const res = await fetch(`${API_BASE}/v1/api-keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });

      if (!res.ok) {
        const text = await res.text();
        setError(text || `Request failed with status ${res.status}`);
        return;
      }

      const data = (await res.json()) as { user_id: string; api_key: string };
      setUserId(data.user_id);
      setApiKey(data.api_key);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = () => {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Navbar />
      <main className="flex min-h-0 flex-1 justify-center overflow-y-auto bg-background px-4 py-8">
        <div className="w-full max-w-xl">
          <Card className="border-border/70 bg-card/90">
            <CardHeader className="space-y-1">
              <h1 className="text-lg font-semibold">Create API key</h1>
              <p className="text-xs text-muted-foreground">
                Enter your email to enroll with QAlityDeep and receive an API key. The key is shown{" "}
                <span className="font-semibold text-foreground">only once</span>—copy and store it
                securely.
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              <form onSubmit={handleSubmit} className="space-y-3">
                <label className="block text-xs font-medium text-muted-foreground">
                  Email address
                </label>
                <div className="relative">
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="pl-8 text-sm"
                    required
                  />
                  <Mail className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                </div>
                <Button
                  type="submit"
                  disabled={!canSubmit}
                  className="mt-1 w-full justify-center"
                >
                  {submitting ? "Creating key…" : "Create API key"}
                </Button>
              </form>

              {error && (
                <div className="rounded-md border border-red-500/40 bg-red-500/5 px-3 py-2 text-xs text-red-400">
                  {error}
                </div>
              )}

              {apiKey && (
                <div className="space-y-2 rounded-md border border-emerald-500/40 bg-emerald-500/5 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs font-semibold text-emerald-300">
                      Your API key (shown only once)
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="xs"
                      onClick={handleCopy}
                      className="h-7 gap-1 rounded-full border-emerald-500/60 bg-emerald-500/10 px-2 text-[11px] text-emerald-100 hover:bg-emerald-500/20"
                    >
                      {copied ? (
                        <>
                          <Check className="h-3.5 w-3.5" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="overflow-x-auto rounded-md bg-black/40 p-2 font-mono text-xs text-emerald-50">
                    <span className="break-all">{apiKey}</span>
                  </div>
                  {userId && (
                    <p className="text-[10px] text-emerald-200/80">
                      Enrolled as user <span className="font-mono">{userId}</span>.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}

