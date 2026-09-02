"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Anchor,
  Shield,
  Clock,
  WifiOff,
  Presentation,
  BarChart3,
  FileText,
  Terminal,
  Layers,
  Sparkles,
  Command,
  History,
  Trash2,
} from "lucide-react";
import { useQuery } from "@/hooks/useQuery";
import { useQueryHistory } from "@/hooks/useQueryHistory";
import { QueryPanel } from "@/components/QueryPanel";
import { SSEConsole } from "@/components/SSEConsole";
import { PDFInspector } from "@/components/PDFInspector";
import { SlideStudio } from "@/components/SlideStudio";
import { EvalDashboard } from "@/components/EvalDashboard";
import { Citation } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function TacticalConsole() {
  const query = useQuery();
  const { history, addQuery, clearHistory } = useQueryHistory();
  const [dtg, setDtg] = useState<string>("");
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [rightView, setRightView] = useState<"pdf" | "telemetry">("pdf");
  const [isSlideStudioOpen, setIsSlideStudioOpen] = useState<boolean>(false);
  const [isEvalDashboardOpen, setIsEvalDashboardOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [stagedDeckTopic, setStagedDeckTopic] = useState<string>("");

  // Record query to history upon completion
  useEffect(() => {
    if ((query.status === "completed" || query.status === "abstained") && query.question) {
      addQuery({
        query: query.question,
        answer: query.answer,
        status: query.status,
      });
    }
  }, [query.status, query.question, query.answer, addQuery]);

  // Live Military Date-Time Group (DTG) Clock
  useEffect(() => {
    const updateDTG = () => {
      const now = new Date();
      const day = String(now.getUTCDate()).padStart(2, "0");
      const hours = String(now.getUTCHours()).padStart(2, "0");
      const minutes = String(now.getUTCMinutes()).padStart(2, "0");
      const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
      const month = months[now.getUTCMonth()];
      const year = now.getUTCFullYear();
      setDtg(`${day}${hours}${minutes}Z ${month} ${year}`);
    };

    updateDTG();
    const interval = setInterval(updateDTG, 1000);
    return () => clearInterval(interval);
  }, []);

  // Global Keyboard Navigation Shortcuts
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is actively typing in an input or textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      if (e.key === "d" || e.key === "D") {
        e.preventDefault();
        setIsSlideStudioOpen((prev) => !prev);
      } else if (e.key === "e" || e.key === "E") {
        e.preventDefault();
        setIsEvalDashboardOpen((prev) => !prev);
      } else if (e.key === "h" || e.key === "H") {
        e.preventDefault();
        setIsHistoryOpen((prev) => !prev);
      } else if (e.key === "t" || e.key === "T") {
        e.preventDefault();
        setRightView((prev) => (prev === "pdf" ? "telemetry" : "pdf"));
      } else if (e.key === "Escape") {
        setIsSlideStudioOpen(false);
        setIsEvalDashboardOpen(false);
        setIsHistoryOpen(false);
      }
    };

    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, []);

  // Forward Sync: when citation is selected in QueryPanel -> switch to PDF Inspector and focus
  const handleCitationSelect = useCallback((citation: Citation) => {
    setSelectedCitation(citation);
    setRightView("pdf");
  }, []);

  // Reverse Sync: when clause in PDF is clicked -> dispatch query to answer panel
  const handleClauseClick = useCallback((clauseText: string, citation: Citation) => {
    query.submitQuery(`Explain regulatory compliance for: "${clauseText}" under ${citation.document}`);
  }, [query]);


  // Request Briefing Deck: Stage topic and open SlideStudio
  const handleRequestDeck = useCallback((topic: string) => {
    setStagedDeckTopic(topic);
    setIsSlideStudioOpen(true);
  }, []);

  return (
    <main className="flex-1 flex flex-col p-3 sm:p-4 md:p-6 max-w-[1780px] w-full mx-auto space-y-4">
      {/* Command Shell Header */}
      <header className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 p-4 rounded-xl bg-[#111C2E] border border-[#233554] shadow-lg">
        {/* Brand & Mission Title */}
        <div className="flex items-center space-x-3.5">
          <div className="h-11 w-11 rounded-lg bg-[#00E5FF]/10 border border-[#00E5FF]/40 flex items-center justify-center text-[#00E5FF] shadow-[0_0_20px_rgba(0,229,255,0.25)] shrink-0">
            <Anchor className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-lg sm:text-xl font-bold tracking-wider text-white font-mono uppercase">
                PROJECT ANCHOR
              </h1>
              <span className="px-2.5 py-0.5 rounded bg-[#00E5FF]/10 border border-[#00E5FF]/30 text-[#00E5FF] text-xs font-mono font-bold">
                C4ISR CONSOLE v1.0
              </span>
            </div>
            <p className="text-xs text-[#94A3B8] font-sans">
              Autonomous Naval Compliance Hub for Operational Regulation // Indian Navy INICAI 2026
            </p>
          </div>
        </div>

        {/* Global Action Tools & Telemetry */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono">
          {/* Query History Trigger (ENH-008) */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsHistoryOpen(true)}
            className="flex items-center space-x-1.5 border-[#00E5FF]/40 text-[#00E5FF] hover:bg-[#00E5FF]/10"
          >
            <History className="h-4 w-4" />
            <span>HISTORY ({history.length})</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.2 rounded bg-[#0B0F19]/60 text-[10px] text-[#00E5FF] border border-[#00E5FF]/30">
              H
            </kbd>
          </Button>

          {/* Slide Studio Trigger */}
          <Button
            variant="cyan"
            size="sm"
            onClick={() => setIsSlideStudioOpen(true)}
            className="flex items-center space-x-1.5 shadow-[0_0_15px_rgba(0,229,255,0.2)]"
          >
            <Presentation className="h-4 w-4" />
            <span>SLIDE STUDIO</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.2 rounded bg-[#0B0F19]/60 text-[10px] text-[#00E5FF] border border-[#00E5FF]/30">
              D
            </kbd>
          </Button>

          {/* Eval Dashboard Trigger */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEvalDashboardOpen(true)}
            className="flex items-center space-x-1.5 border-[#10B981]/50 text-[#10B981] hover:bg-[#10B981]/10"
          >
            <BarChart3 className="h-4 w-4" />
            <span>EVAL SCORECARD</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.2 rounded bg-[#0B0F19]/60 text-[10px] text-[#10B981] border border-[#10B981]/30">
              E
            </kbd>
          </Button>

          {/* DTG Clock */}
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#0B0F19] border border-[#233554] text-[#CCD6F6]">
            <Clock className="h-3.5 w-3.5 text-[#00E5FF]" />
            <span>DTG: {dtg || "010000Z SEP 2026"}</span>
          </div>

          {/* Air-Gap Status */}
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#0B0F19] border border-[#10B981]/40 text-[#10B981]">
            <WifiOff className="h-3.5 w-3.5 text-[#10B981]" />
            <span>AIR-GAPPED</span>
          </div>
        </div>
      </header>

      {/* Main 60/40 Tactical Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-1 min-h-[720px]">
        {/* Left Column: QueryPanel (60% / 7 Cols) */}
        <section className="lg:col-span-7 flex flex-col min-h-[640px]">
          <QueryPanel
            query={query}
            onCitationSelect={handleCitationSelect}
            onRequestDeck={handleRequestDeck}
          />
        </section>

        {/* Right Column: PDFInspector or SSEConsole (40% / 5 Cols) */}
        <section className="lg:col-span-5 flex flex-col min-h-[640px] space-y-2">
          {/* Right Pane View Switcher Tabs */}
          <div className="flex items-center justify-between p-1.5 rounded-lg bg-[#111C2E] border border-[#233554] text-xs font-mono">
            <div className="flex items-center space-x-1.5">
              <button
                onClick={() => setRightView("pdf")}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                  rightView === "pdf"
                    ? "bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/40 shadow-[0_0_10px_rgba(0,229,255,0.15)]"
                    : "text-[#94A3B8] hover:text-white"
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                <span>PDF CITATION INSPECTOR</span>
              </button>

              <button
                onClick={() => setRightView("telemetry")}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                  rightView === "telemetry"
                    ? "bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/40 shadow-[0_0_10px_rgba(0,229,255,0.15)]"
                    : "text-[#94A3B8] hover:text-white"
                }`}
              >
                <Terminal className="h-3.5 w-3.5" />
                <span>SSE TELEMETRY CONSOLE</span>
              </button>
            </div>

            <kbd className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-[#0B0F19] text-[10px] text-[#64748B] border border-[#233554]">
              Tab: T
            </kbd>
          </div>

          {/* Right Pane View Content */}
          <div className="flex-1 flex flex-col min-h-0">
            {rightView === "pdf" ? (
              <PDFInspector
                selectedCitation={selectedCitation}
                onClauseClick={handleClauseClick}
                className="flex-1"
              />
            ) : (
              <SSEConsole query={query} className="flex-1" />
            )}
          </div>
        </section>
      </div>

      {/* AutoDeck AI Slide Studio Modal */}
      <SlideStudio
        isOpen={isSlideStudioOpen}
        onClose={() => setIsSlideStudioOpen(false)}
        initialTopic={stagedDeckTopic}
      />

      {/* Live Statutory Evaluation Dashboard Drawer */}
      <EvalDashboard
        isOpen={isEvalDashboardOpen}
        onClose={() => setIsEvalDashboardOpen(false)}
      />

      {/* Query History Slide-Over Drawer (ENH-008) */}
      {isHistoryOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-md bg-[#111C2E] border-l border-[#233554] p-5 flex flex-col h-full shadow-2xl animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between pb-4 border-b border-[#233554]">
              <div className="flex items-center space-x-2 text-cyan-400 font-mono font-bold text-sm">
                <History className="h-4 w-4" />
                <span>QUERY HISTORY ({history.length})</span>
              </div>
              <div className="flex items-center space-x-2">
                {history.length > 0 && (
                  <button
                    onClick={clearHistory}
                    className="p-1.5 text-xs text-red-400 hover:bg-red-950/40 rounded transition-colors flex items-center gap-1"
                    title="Clear History"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Clear</span>
                  </button>
                )}
                <Button size="sm" variant="ghost" onClick={() => setIsHistoryOpen(false)}>
                  ✕
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto py-4 space-y-2.5">
              {history.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground text-xs font-mono">
                  No previous queries recorded in this session.
                </div>
              ) : (
                history.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      query.submitQuery(item.query);
                      setIsHistoryOpen(false);
                    }}
                    className="p-3 rounded-lg bg-[#0B0F19] border border-[#233554] hover:border-cyan-400/50 cursor-pointer transition-colors space-y-1.5 group"
                  >
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground font-mono">
                      <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                      <span className={item.status === "completed" ? "text-emerald-400" : "text-amber-400"}>
                        {item.status?.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-xs text-foreground font-medium group-hover:text-cyan-400 transition-colors line-clamp-2">
                      {item.query}
                    </p>
                    {item.answer && (
                      <p className="text-[11px] text-muted-foreground line-clamp-2">
                        {item.answer}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
