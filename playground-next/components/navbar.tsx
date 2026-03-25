"use client";

import { Search, MessageCircle, Shield, Activity, HelpCircle, Gift, ChevronDown, KeyRound } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 flex h-16 shrink-0 items-center gap-4 border-b border-border bg-background px-6">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/20 text-primary">
          <span className="text-sm font-bold">Q</span>
        </div>
        <span className="text-sm font-semibold">QAlityDeep docs.</span>
      </div>

      <div className="flex flex-1 justify-center px-4">
        <div className="relative w-full max-w-xl">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search"
            className="h-9 w-full rounded-md bg-muted/50 pl-9 pr-4"
          />
        </div>
      </div>

      <div className="flex items-center gap-1">
        <Link href="/create-api-key">
          <Button
            variant="outline"
            size="sm"
            className="mr-1 gap-1.5 rounded-full border-primary/40 bg-primary/10 text-xs text-primary hover:bg-primary/20"
          >
            <KeyRound className="h-4 w-4" />
            Get API key
          </Button>
        </Link>
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
          <MessageCircle className="mr-1.5 h-4 w-4" />
          Ask AI
        </Button>
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
          <Shield className="mr-1.5 h-4 w-4" />
          Trust Center
        </Button>
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
          <Activity className="mr-1.5 h-4 w-4" />
          Status
        </Button>
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
          <HelpCircle className="mr-1.5 h-4 w-4" />
          Support
        </Button>
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
          <Gift className="mr-1.5 h-4 w-4" />
          Get a demo
        </Button>
        <Button
          variant="secondary"
          size="sm"
          className="gap-1.5 rounded-full bg-muted/80 pl-4 pr-3 text-foreground hover:bg-muted"
        >
          Platform
          <ChevronDown className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
