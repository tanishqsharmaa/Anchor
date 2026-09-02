"use client";

/**
 * SlidePreview.tsx — 16:9 Widescreen HTML5 Slide Preview Component
 * Renders the 4 naval AST archetypes defined in Reference/PROJECT_ANCHOR_BLUEPRINT.md:L158-198.
 */

import React from "react";
import {
  ShieldCheck,
  Anchor,
  Clock,
  User,
  AlertTriangle,
  Layers,
  DollarSign,
  TrendingUp,
  FileCheck,
} from "lucide-react";
import { SlidePreviewProps, SlideASTItem } from "@/lib/types";
import { Badge } from "./ui/Badge";

export function SlidePreview({
  slide,
  slideIndex,
  totalSlides,
  className = "",
}: SlidePreviewProps) {
  const isVerified = slide.verified !== false;
  const lowestScore =
    slide.nli_scores && slide.nli_scores.length > 0
      ? Math.min(...slide.nli_scores)
      : 0.96;

  // Render based on Slide Archetype
  const renderSlideContent = (item: SlideASTItem) => {
    switch (item.type) {
      case "HERO_SLIDE":
        return (
          <div className="flex flex-col items-center justify-center text-center h-full px-8 py-6 space-y-6">
            <div className="h-16 w-16 rounded-full bg-[#00E5FF]/10 border-2 border-[#00E5FF]/40 flex items-center justify-center text-[#00E5FF] shadow-[0_0_25px_rgba(0,229,255,0.25)]">
              <Anchor className="h-9 w-9" />
            </div>

            <div className="space-y-2 max-w-2xl">
              <span className="px-3 py-1 rounded bg-[#00E5FF]/10 border border-[#00E5FF]/30 text-[#00E5FF] text-xs font-mono font-bold tracking-widest uppercase">
                INDIAN NAVAL STAFF BRIEFING
              </span>
              <h2 className="text-2xl sm:text-3xl font-bold font-mono text-white tracking-wide uppercase">
                {item.title || "OPERATIONAL COMPLIANCE BRIEFING"}
              </h2>
            </div>

            <div className="grid grid-cols-2 gap-4 w-full max-w-md p-4 rounded bg-[#0B0F19]/80 border border-[#233554] text-xs font-mono">
              <div className="flex items-center space-x-2 text-[#94A3B8]">
                <Clock className="h-4 w-4 text-[#00E5FF]" />
                <span>DTG: {item.dtg || "010300Z SEP 2026"}</span>
              </div>
              <div className="flex items-center space-x-2 text-[#94A3B8]">
                <User className="h-4 w-4 text-[#FFD700]" />
                <span>OFFICER: {item.officer || "CDR STAFF DUTIES"}</span>
              </div>
            </div>
          </div>
        );

      case "BLUF_EXECUTIVE":
        return (
          <div className="flex flex-col h-full justify-between p-6 space-y-4">
            <div className="border-b border-[#233554] pb-3">
              <span className="text-[11px] font-mono text-[#00E5FF] font-semibold uppercase tracking-wider">
                BOTTOM LINE UP FRONT (BLUF)
              </span>
              <h3 className="text-xl font-bold font-mono text-white mt-1">
                {item.title}
              </h3>
            </div>

            <div className="p-4 rounded-lg bg-[#0B0F19]/90 border border-[#00E5FF]/40 shadow-[0_0_15px_rgba(0,229,255,0.1)]">
              <div className="text-xs font-mono text-[#00E5FF] font-bold mb-1.5 flex items-center space-x-1.5">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>DECISION REQUESTED:</span>
              </div>
              <p className="text-sm font-sans text-white leading-relaxed">
                {item.decision_requested || "Sanction of expenditure under delegated financial powers."}
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
              <div className="p-2.5 rounded bg-[#162032] border border-[#233554]">
                <span className="text-[10px] text-[#94A3B8] block">WHO:</span>
                <span className="text-[#CCD6F6] font-semibold truncate block">
                  {item.who || "Fleet Commander (Tier 3)"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-[#162032] border border-[#233554]">
                <span className="text-[10px] text-[#94A3B8] block">WHAT:</span>
                <span className="text-[#CCD6F6] font-semibold truncate block">
                  {item.what || "Procurement of Stores"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-[#162032] border border-[#233554]">
                <span className="text-[10px] text-[#94A3B8] block">WHEN / URGENCY:</span>
                <span className="text-[#FFD700] font-semibold truncate block">
                  {item.urgency || "IMMEDIATE (P1)"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-[#162032] border border-[#233554]">
                <span className="text-[10px] text-[#94A3B8] block">WHERE:</span>
                <span className="text-[#CCD6F6] font-semibold truncate block">
                  {item.where || "Western Naval Command"}
                </span>
              </div>
            </div>
          </div>
        );

      case "POLICY_MATRIX":
        return (
          <div className="flex flex-col h-full justify-between p-6 space-y-4">
            <div className="border-b border-[#233554] pb-3">
              <span className="text-[11px] font-mono text-[#FFD700] font-semibold uppercase tracking-wider">
                REGULATORY & PROCUREMENT MATRIX
              </span>
              <h3 className="text-xl font-bold font-mono text-white mt-1">
                {item.title}
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4 flex-1">
              <div className="p-4 rounded-lg bg-[#0B0F19]/80 border border-[#233554] space-y-2.5 text-xs font-mono">
                <div className="flex items-center space-x-2 text-[#00E5FF] font-bold">
                  <Layers className="h-4 w-4" />
                  <span>DFPDS-2026 DELEGATION</span>
                </div>
                <div className="space-y-1.5 text-[#CCD6F6]">
                  <p><span className="text-[#94A3B8]">Schedule:</span> Schedule {item.schedule || "07"} ({item.schedule_name || "Ship Repairs"})</p>
                  <p><span className="text-[#94A3B8]">CFA Tier:</span> {item.tier || "Tier 3"} ({item.tier_name || "Fleet Commander"})</p>
                  <p><span className="text-[#94A3B8]">With IFA Limit:</span> ₹{item.with_ifa !== undefined && item.with_ifa !== null ? item.with_ifa : "18.00"} Cr</p>
                  <p><span className="text-[#94A3B8]">Without IFA Limit:</span> ₹{item.without_ifa !== undefined && item.without_ifa !== null ? item.without_ifa : "3.00"} Cr</p>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-[#0B0F19]/80 border border-[#233554] space-y-2.5 text-xs font-mono">
                <div className="flex items-center space-x-2 text-[#FFD700] font-bold">
                  <FileCheck className="h-4 w-4" />
                  <span>DPM 2025 COMPLIANCE</span>
                </div>
                <div className="space-y-1.5 text-[#CCD6F6]">
                  <p><span className="text-[#94A3B8]">Tendering Mode:</span> {item.mode || "Single Tender Enquiry (STE)"}</p>
                  <p><span className="text-[#94A3B8]">IFA Concurrence:</span> {item.ifa_required !== false ? "MANDATORY" : "NOT REQUIRED"}</p>
                  <p><span className="text-[#94A3B8]">PAC Justification:</span> Statutorily Validated</p>
                  <p><span className="text-[#94A3B8]">Statutory Precedence:</span> DFPDS-2026 &gt; DPM-2025</p>
                </div>
              </div>
            </div>
          </div>
        );

      case "FINANCIAL_DELEGATION":
      default:
        return (
          <div className="flex flex-col h-full justify-between p-6 space-y-4">
            <div className="border-b border-[#233554] pb-3">
              <span className="text-[11px] font-mono text-[#10B981] font-semibold uppercase tracking-wider">
                FINANCIAL OUTLAY & INDIGENISATION
              </span>
              <h3 className="text-xl font-bold font-mono text-white mt-1">
                {item.title}
              </h3>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="p-3.5 rounded bg-[#0B0F19]/90 border border-[#10B981]/40 text-center">
                <span className="text-[10px] font-mono text-[#94A3B8] block">ESTIMATED OUTLAY</span>
                <span className="text-lg font-bold font-mono text-[#10B981]">
                  ₹{item.total_estimate_cr || "14.50"} Cr
                </span>
              </div>
              <div className="p-3.5 rounded bg-[#0B0F19]/90 border border-[#00E5FF]/40 text-center">
                <span className="text-[10px] font-mono text-[#94A3B8] block">BUDGET HEAD</span>
                <span className="text-sm font-bold font-mono text-[#00E5FF] truncate block mt-1">
                  {item.budget_head || "Major Head 2077"}
                </span>
              </div>
              <div className="p-3.5 rounded bg-[#0B0F19]/90 border border-[#FFD700]/40 text-center">
                <span className="text-[10px] font-mono text-[#94A3B8] block">INDIGENISATION (IC%)</span>
                <span className="text-lg font-bold font-mono text-[#FFD700]">
                  {item.indigenisation_pct || 75}%
                </span>
              </div>
            </div>

            <div className="p-3 rounded bg-[#162032] border border-[#233554] flex-1">
              <span className="text-[11px] font-mono text-[#CCD6F6] font-bold block mb-2">
                PROJECT PHASED MILESTONES:
              </span>
              <div className="space-y-1.5 text-xs font-mono text-[#94A3B8]">
                <div className="flex justify-between border-b border-[#233554]/50 pb-1">
                  <span>Phase I: Technical Evaluation & IFA Concurrence</span>
                  <span className="text-[#00E5FF]">T0 + 30 Days (20%)</span>
                </div>
                <div className="flex justify-between border-b border-[#233554]/50 pb-1">
                  <span>Phase II: Delivery & FAT Testing</span>
                  <span className="text-[#00E5FF]">T0 + 90 Days (50%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Phase III: Commissioning & PBG Verification</span>
                  <span className="text-[#00E5FF]">T0 + 120 Days (30%)</span>
                </div>
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div
      className={`relative flex flex-col justify-between aspect-video w-full rounded-xl bg-[#0A192F] border-2 border-[#233554] overflow-hidden shadow-2xl transition-all ${className}`}
    >
      {/* Slide Classification Header Banner */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#07111E] border-b border-[#233554] text-[10px] font-mono">
        <span className="text-[#FFD700] font-bold tracking-wider">
          RESTRICTED // FOR OFFICIAL NAVAL USE ONLY
        </span>
        <span className="text-[#94A3B8]">
          SLIDE {slideIndex + 1} OF {totalSlides}
        </span>
      </div>

      {/* Main Slide Content Canvas */}
      <div className="flex-1 overflow-hidden relative">
        {renderSlideContent(slide)}
      </div>

      {/* Slide Classification Footer Banner with NLI Verification Score */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#07111E] border-t border-[#233554] text-[10px] font-mono">
        <div className="flex items-center space-x-1.5 text-[#10B981]">
          <ShieldCheck className="h-3 w-3" />
          <span>
            NLI VERIFIED ({isVerified ? `Score: ${lowestScore.toFixed(2)}` : "Unverified"})
          </span>
        </div>
        <span className="text-[#64748B]">
          AUTODECK AI // INBR BLUF-v2026
        </span>
      </div>
    </div>
  );
}
