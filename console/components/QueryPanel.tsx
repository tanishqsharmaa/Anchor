"use client";

/**
 * QueryPanel.tsx — Regulatory Query Dispatch & Answer Presentation Panel
 * Supports Path A (Deterministic CFA tables) and Path B (NLI-certified generative answers).
 */

import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  Send,
  X,
  Copy,
  Check,
  ShieldAlert,
  ShieldCheck,
  Zap,
  FileText,
  Table as TableIcon,
  HelpCircle,
} from "lucide-react";
import { UseQueryResult } from "@/hooks/useQuery";
import { Citation } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CitationBadge } from "@/components/ui/CitationBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { CitationPanel } from "@/components/CitationPanel";

interface QueryPanelProps {
  query: UseQueryResult;
  onCitationSelect?: (citation: Citation) => void;
  onRequestDeck?: (topic: string) => void;
}

const QUICK_CHIPS = [
  {
    label: "Sch 7 Drones (Fleet Cdr)",
    query: "What is the financial limit for a Fleet Commander under Schedule 7 for Tactical Drones with IFA?",
    badge: "Path A · Sch 7",
  },
  {
    label: "Sch 1 Capital Repairs",
    query: "What is the financial power under Schedule 1 for Major Refits and Repairs of Aircraft?",
    badge: "Path A · Sch 1",
  },
  {
    label: "Sch 18 Yard Crafts",
    query: "What are the financial powers under Schedule 18 for Berthing and Yard Craft chartering?",
    badge: "Path A · Sch 18",
  },
  {
    label: "CO Frigate GeM Bypass",
    query: "Can a CO Frigate invoke emergency procurement powers to bypass GeM for critical propulsion repair?",
    badge: "Path B · RAG + NLI",
  },
  {
    label: "PAC Sole Source (DPM)",
    query: "What are the mandatory conditions and PAC justification rules under DPM 2025 Chapter 3?",
    badge: "Path B · DPM 2025",
  },
  {
    label: "Out of Domain (OOD)",
    query: "What is the capital budget allocation for INS Vishal carrier construction in FY 2027?",
    badge: "Abstain Test",
  },
];

export const QueryPanel: React.FC<QueryPanelProps> = ({
  query,
  onCitationSelect,
  onRequestDeck,
}) => {
  const [inputVal, setInputVal] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    status,
    question,
    answer,
    routeType,
    citations,
    verifiedSentences,
    structuredResult,
    refusalReason,
    refusalExplanation,
    remedySuggestions,
    errorMessage,
    submitQuery,
    resetQuery,
  } = query;

  // Keyboard shortcut: '/' focuses the input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === "/" &&
        document.activeElement !== inputRef.current &&
        !["INPUT", "TEXTAREA"].includes((document.activeElement as HTMLElement)?.tagName)
      ) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputVal.trim() && status !== "streaming" && status !== "submitting") {
      submitQuery(inputVal.trim());
    }
  };

  const handleChipClick = (queryText: string) => {
    setInputVal(queryText);
    submitQuery(queryText);
  };

  const handleCopyAnswer = () => {
    if (!answer) return;
    navigator.clipboard.writeText(answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-[#111C2E] rounded-lg border border-[#233554] overflow-hidden">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#233554] bg-[#0E1726]">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded bg-[#00E5FF]/10 border border-[#00E5FF]/30 text-[#00E5FF]">
            <Zap className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-wider text-white font-mono uppercase">
              Regulatory Query Dispatch
            </h2>
            <p className="text-[11px] text-[#94A3B8]">
              Dual-Path Engine: Deterministic SQL Resolver & NLI-Gated RAG
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {routeType === "structured" && (
            <Badge variant="cyan" dot>
              Path A · SQL Resolved
            </Badge>
          )}
          {routeType === "interpretive" && (
            <Badge variant="green" dot>
              Path B · NLI Verified
            </Badge>
          )}
          {status === "abstained" && (
            <Badge variant="red" dot>
              Certified Abstention
            </Badge>
          )}
        </div>
      </div>

      {/* Query Search Bar */}
      <form onSubmit={handleSubmit} className="p-4 border-b border-[#233554] bg-[#111C2E]">
        <div className="relative flex items-center">
          <Search className="absolute left-3.5 h-4 w-4 text-[#94A3B8] pointer-events-none" />
          <input
            ref={inputRef}
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Search regulations (e.g. Schedule 7, DPM PAC limits, or press '/' to focus)..."
            disabled={status === "streaming" || status === "submitting"}
            className="w-full bg-[#0B0F19] text-white placeholder-[#64748B] pl-10 pr-24 py-2.5 rounded-lg border border-[#233554] text-sm focus:outline-none focus:border-[#00E5FF] focus:ring-1 focus:ring-[#00E5FF] transition-all font-sans"
          />

          <div className="absolute right-2 flex items-center space-x-1.5">
            {inputVal && (
              <button
                type="button"
                onClick={() => {
                  setInputVal("");
                  resetQuery();
                }}
                className="p-1 text-[#94A3B8] hover:text-white transition"
              >
                <X className="h-4 w-4" />
              </button>
            )}
            <Button
              type="submit"
              size="sm"
              variant="primary"
              isLoading={status === "streaming" || status === "submitting"}
              disabled={!inputVal.trim()}
              rightIcon={<Send className="h-3.5 w-3.5" />}
            >
              Dispatch
            </Button>
          </div>
        </div>

        {/* Quick Shortcut Chips */}
        <div className="flex items-center space-x-2 mt-3 overflow-x-auto pb-1 text-xs">
          <span className="text-[#64748B] uppercase tracking-wider text-[10px] font-mono shrink-0">
            Quick Queries:
          </span>
          {QUICK_CHIPS.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleChipClick(chip.query)}
              className="shrink-0 px-2.5 py-1 rounded bg-[#162032] border border-[#233554] hover:border-[#00E5FF]/60 hover:text-white text-[#CCD6F6] text-xs font-mono transition"
            >
              {chip.label}
            </button>
          ))}
        </div>
      </form>

      {/* Main Content / Answer Container */}
      <div className="flex-1 p-5 overflow-y-auto terminal-scroll flex flex-col space-y-4">
        {/* Empty State */}
        {status === "idle" && (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 space-y-4 text-[#94A3B8]">
            <div className="h-12 w-12 rounded-full bg-[#162032] border border-[#233554] flex items-center justify-center text-[#00E5FF]">
              <HelpCircle className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
                Tactical Regulatory Intelligence Active
              </h3>
              <p className="text-xs text-[#94A3B8] max-w-md mt-1">
                Enter a naval procurement query above or select a preset chip. Structured queries resolve via deterministic SQL tables, while interpretive queries are synthesized and verified by sentence-level DeBERTa NLI.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg mt-2 text-left">
              <div className="p-3 bg-[#0B0F19] rounded border border-[#233554]">
                <div className="flex items-center space-x-2 text-[#00E5FF] text-xs font-mono font-bold">
                  <TableIcon className="h-3.5 w-3.5" />
                  <span>Path A: Zero-Hallucination SQL</span>
                </div>
                <p className="text-[11px] text-[#64748B] mt-1">
                  100% exact math over all 32 DFPDS-2026 schedules and CFA delegation tiers.
                </p>
              </div>
              <div className="p-3 bg-[#0B0F19] rounded border border-[#233554]">
                <div className="flex items-center space-x-2 text-[#10B981] text-xs font-mono font-bold">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Path B: NLI-Verified RAG</span>
                </div>
                <p className="text-[11px] text-[#64748B] mt-1">
                  DeBERTa entailment gate (≥0.85) with SHA-256 byte anchors and certified abstention.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Loading Skeleton */}
        {status === "submitting" && (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 text-xs font-mono text-[#00E5FF]">
              <span className="h-2 w-2 rounded-full bg-[#00E5FF] animate-ping" />
              <span>Routing and dispatching query to sovereign pipeline...</span>
            </div>
            <Skeleton height={24} width="60%" />
            <Skeleton height={80} />
            <Skeleton height={40} width="40%" />
          </div>
        )}

        {/* Streaming & Completed Answer View */}
        {(status === "streaming" || status === "completed") && (
          <div className="flex flex-col space-y-4">
            {/* Active Question Badge */}
            {question && (
              <div className="p-3 rounded bg-[#0B0F19] border border-[#233554] text-xs font-mono text-[#CCD6F6]">
                <span className="text-[#00E5FF] font-bold">QUERY: </span>
                {question}
              </div>
            )}

            {/* Path A Structured CFA Limits Table */}
            {structuredResult && (
              <div className="p-4 rounded-lg bg-[#0B0F19] border border-[#00E5FF]/40 shadow-[0_0_15px_rgba(0,229,255,0.1)]">
                <div className="flex items-center justify-between border-b border-[#233554] pb-2 mb-3">
                  <div className="flex items-center space-x-2">
                    <TableIcon className="h-4 w-4 text-[#00E5FF]" />
                    <span className="text-xs font-bold font-mono text-white tracking-wider">
                      STATUTORY FINANCIAL DELEGATION TABLE
                    </span>
                  </div>
                  <Badge variant="cyan" size="sm">
                    {structuredResult.schedule_name || `Schedule ${structuredResult.schedule_no}`}
                  </Badge>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead>
                      <tr className="border-b border-[#233554] text-[#94A3B8]">
                        <th className="py-2 px-3">CFA Tier</th>
                        <th className="py-2 px-3">Competent Authority</th>
                        <th className="py-2 px-3 text-right">With IFA</th>
                        <th className="py-2 px-3 text-right">Without IFA</th>
                        {structuredResult.pac_limit !== undefined && (
                          <th className="py-2 px-3 text-right">PAC Limit</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-[#162032] text-white bg-[#111C2E]/60">
                        <td className="py-2 px-3 font-bold text-[#00E5FF]">
                          {structuredResult.tier || "Tier"}
                        </td>
                        <td className="py-2 px-3">
                          {structuredResult.tier_name || "Naval Appointment"}
                        </td>
                        <td className="py-2 px-3 text-right font-bold text-[#10B981]">
                          {structuredResult.with_ifa !== null && structuredResult.with_ifa !== undefined
                            ? `₹${Number(structuredResult.with_ifa).toFixed(2)} Cr`
                            : "Full Powers"}
                        </td>
                        <td className="py-2 px-3 text-right text-[#FFD700]">
                          {structuredResult.without_ifa !== null && structuredResult.without_ifa !== undefined
                            ? `₹${Number(structuredResult.without_ifa).toFixed(2)} Cr`
                            : "Nil"}
                        </td>
                        {structuredResult.pac_limit !== undefined && (
                          <td className="py-2 px-3 text-right text-[#CCD6F6]">
                            {structuredResult.pac_limit !== null
                              ? `₹${Number(structuredResult.pac_limit).toFixed(2)} Cr`
                              : "N/A"}
                          </td>
                        )}
                      </tr>
                    </tbody>
                  </table>
                </div>

                {structuredResult.notes && (
                  <p className="text-[11px] text-[#94A3B8] font-sans mt-2 italic">
                    Note: {structuredResult.notes}
                  </p>
                )}
              </div>
            )}

            {/* Answer Display (Formatted / Per-Sentence Highlighted) */}
            <div className="p-4 rounded-lg bg-[#0B0F19] border border-[#233554] text-sm text-[#E5E7EB] leading-relaxed relative group">
              <div className="flex items-center justify-between border-b border-[#233554] pb-2 mb-3">
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4 text-[#10B981]" />
                  <span className="text-xs font-bold font-mono text-white tracking-wider">
                    {routeType === "structured"
                      ? "DETERMINISTIC BLUF STATEMENT"
                      : "NLI-VERIFIED REGULATORY SYNTHESIS"}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleCopyAnswer}
                    leftIcon={copied ? <Check className="h-3.5 w-3.5 text-[#10B981]" /> : <Copy className="h-3.5 w-3.5" />}
                  >
                    {copied ? "Copied" : "Copy"}
                  </Button>
                  {onRequestDeck && (
                    <Button
                      size="sm"
                      variant="gold"
                      onClick={() => onRequestDeck(question)}
                    >
                      Generate BLUF Deck
                    </Button>
                  )}
                </div>
              </div>

              {/* Per-Sentence Verification Highlighting */}
              {verifiedSentences.length > 0 ? (
                <div className="space-y-2">
                  {verifiedSentences.map((s, idx) => (
                    <div key={idx} className="flex items-start space-x-2">
                      <span className="flex-1">{s.text}</span>
                      <Badge
                        variant={s.status === "certified" ? "certified" : s.status === "regen" ? "regen" : "abstain"}
                        size="sm"
                        className="shrink-0"
                      >
                        {s.status === "certified"
                          ? `CERTIFIED ${s.nliScore ? `(${(s.nliScore * 100).toFixed(0)}%)` : ""}`
                          : s.status?.toUpperCase()}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="whitespace-pre-wrap font-sans">{answer || "Awaiting synthesis..."}</div>
              )}
            </div>

            {/* Citations Cross-Reference Section (ENH-009) */}
            {citations.length > 0 && (
              <div className="p-4 rounded-lg bg-[#0B0F19] border border-[#233554]">
                <CitationPanel citations={citations} onSelectCitation={onCitationSelect} />
              </div>
            )}
          </div>
        )}

        {/* Certified Abstention View */}
        {status === "abstained" && (
          <div className="p-5 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/40 shadow-[0_0_20px_rgba(239,68,68,0.15)] flex flex-col space-y-3">
            <div className="flex items-center space-x-2.5 text-[#EF4444]">
              <ShieldAlert className="h-5 w-5" />
              <h3 className="text-sm font-bold font-mono uppercase tracking-wider">
                Certified Abstention // Refusal Directive
              </h3>
            </div>
            <p className="text-xs text-[#CCD6F6] font-mono leading-relaxed">
              Reason Code: <span className="text-[#EF4444] font-bold">{refusalReason}</span>
            </p>
            <p className="text-xs text-[#E5E7EB] leading-relaxed">
              {refusalExplanation}
            </p>
            {remedySuggestions.length > 0 && (
              <div className="p-3 bg-[#0B0F19]/60 rounded border border-[#EF4444]/20 text-xs text-[#94A3B8] space-y-1">
                <span className="font-mono text-[#CCD6F6] font-semibold">Suggested Refinements:</span>
                <ul className="list-disc list-inside space-y-0.5">
                  {remedySuggestions.map((sug, idx) => (
                    <li key={idx}>{sug}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Error State */}
        {status === "error" && (
          <div className="p-4 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444] space-y-2">
            <div className="flex items-center space-x-2 font-bold font-mono">
              <ShieldAlert className="h-4 w-4" />
              <span>PIPELINE EXECUTION ERROR</span>
            </div>
            <p className="text-[#CCD6F6]">{errorMessage}</p>
            <Button size="sm" variant="danger" onClick={() => submitQuery(inputVal)}>
              Retry Dispatch
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};
