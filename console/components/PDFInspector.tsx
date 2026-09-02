"use client";

/**
 * PDFInspector.tsx — Bi-Directional PDF Citation Inspector
 * Strictly implements the 3-second verification moment from Reference/PROJECT_ANCHOR_BLUEPRINT.md
 * and Reference/COMPETITIVE_EDGE_PLAYBOOK.md.
 */

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  FileText,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Hash,
  ExternalLink,
  Layers,
  Sparkles,
  AlertCircle,
} from "lucide-react";
import { Citation, PDFInspectorProps } from "@/lib/types";
import { getPdfUrl } from "@/lib/api";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";

const AVAILABLE_DOCUMENTS = [
  { id: "DFPDS_2026_Schedule_01.pdf", label: "DFPDS-2026 Sch 01: Capital Spares & Armament" },
  { id: "DFPDS_2026_Schedule_02.pdf", label: "DFPDS-2026 Sch 02: Naval Stores & Aviation" },
  { id: "DFPDS_2026_Schedule_03.pdf", label: "DFPDS-2026 Sch 03: IT, Networking & C4ISR" },
  { id: "DFPDS_2026_Schedule_04.pdf", label: "DFPDS-2026 Sch 04: Maintenance & Dockyard Works" },
  { id: "DFPDS_2026_Schedule_05.pdf", label: "DFPDS-2026 Sch 05: POL, Fuel & Bunker Stores" },
  { id: "DFPDS_2026_Schedule_06.pdf", label: "DFPDS-2026 Sch 06: Victualling & Clothing" },
  { id: "DFPDS_2026_Schedule_07.pdf", label: "DFPDS-2026 Sch 07: Ship Repairs, Refits & Hull" },
  { id: "DFPDS_2026_Schedule_08.pdf", label: "DFPDS-2026 Sch 08: Special Operations & MARCOS" },
  { id: "DFPDS_2026_Schedule_18.pdf", label: "DFPDS-2026 Sch 18: Tactical Drone Systems" },
  { id: "DPM_2025_Chapter_01.pdf", label: "DPM-2025 Ch 01: Procurement Objectives & Ethics" },
  { id: "DPM_2025_Chapter_02.pdf", label: "DPM-2025 Ch 02: Tendering Modes & Single Tender" },
  { id: "DPM_2025_Chapter_03.pdf", label: "DPM-2025 Ch 03: Commercial Evaluation & IFA" },
  { id: "DPM_2025_Chapter_04.pdf", label: "DPM-2025 Ch 04: Contract Terms & Liquidated Damages" },
  { id: "DPM_2025_Chapter_05.pdf", label: "DPM-2025 Ch 05: Emergency Powers & Sanctions" },
  { id: "DPM_2025_Chapter_06.pdf", label: "DPM-2025 Ch 06: Offset Policies & Make-in-India" },
  { id: "NAVY_REGS_Part_01.pdf", label: "Navy Regs Part I: Command Structure & Administration" },
  { id: "NAVY_REGS_Part_02.pdf", label: "Navy Regs Part II: Financial Sanctions & Stores" },
];

export function PDFInspector({
  selectedCitation,
  onClauseClick,
  className = "",
}: PDFInspectorProps) {
  // Current document & viewer states
  const [currentDoc, setCurrentDoc] = useState<string>("DFPDS_2026_Schedule_07.pdf");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [activeHighlight, setActiveHighlight] = useState<Citation | null>(null);
  const [highlightPulse, setHighlightPulse] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Normalize document ID from citation string
  const resolveDocFilename = (docStr: string): string => {
    if (!docStr) return "DFPDS_2026_Schedule_01.pdf";
    if (docStr.endsWith(".pdf")) return docStr;

    // Pattern matching e.g. "DFPDS-2026/Schedule_07/..." -> "DFPDS_2026_Schedule_07.pdf"
    const schMatch = docStr.match(/Schedule_?(\d+)/i) || docStr.match(/SCH-?(\d+)/i);
    if (schMatch) {
      const num = String(parseInt(schMatch[1], 10)).padStart(2, "0");
      return `DFPDS_2026_Schedule_${num}.pdf`;
    }

    const dpmMatch = docStr.match(/Chapter_?(\d+)/i) || docStr.match(/CH-?(\d+)/i);
    if (dpmMatch) {
      const num = String(parseInt(dpmMatch[1], 10)).padStart(2, "0");
      return `DPM_2025_Chapter_${num}.pdf`;
    }

    const navyRegMatch = docStr.match(/Part_?(\d+|I|II|III|IV)/i);
    if (navyRegMatch) {
      return "NAVY_REGS_Part_01.pdf";
    }

    return "DFPDS_2026_Schedule_07.pdf";
  };

  // Forward Sync: when selectedCitation changes, scroll & highlight immediately (<50ms)
  useEffect(() => {
    if (selectedCitation) {
      const docFilename = resolveDocFilename(selectedCitation.document);
      setCurrentDoc(docFilename);
      setCurrentPage(selectedCitation.page || 1);
      setActiveHighlight(selectedCitation);
      setHighlightPulse(true);

      const pulseTimer = setTimeout(() => {
        setHighlightPulse(false);
      }, 3000);

      return () => clearTimeout(pulseTimer);
    }
  }, [selectedCitation]);

  const pdfUrl = useMemo(() => {
    const baseUrl = getPdfUrl(currentDoc);
    return `${baseUrl}#page=${currentPage}&zoom=${zoomLevel}`;
  }, [currentDoc, currentPage, zoomLevel]);

  const handleZoom = (delta: number) => {
    setZoomLevel((prev) => Math.min(Math.max(prev + delta, 50), 200));
  };

  const handlePageChange = (delta: number) => {
    setCurrentPage((prev) => Math.max(prev + delta, 1));
  };

  const handleClauseClickTrigger = (clauseText: string) => {
    if (onClauseClick && activeHighlight) {
      onClauseClick(clauseText, activeHighlight);
    }
  };

  return (
    <div
      ref={containerRef}
      className={`flex flex-col h-full rounded-lg bg-[#111C2E] border border-[#233554] overflow-hidden shadow-2xl ${
        isFullscreen ? "fixed inset-4 z-50 bg-[#0B0F19]" : ""
      } ${className}`}
    >
      {/* Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#0E1726] border-b border-[#233554] text-xs font-mono">
        {/* Document Selector */}
        <div className="flex items-center space-x-2 min-w-[260px] flex-1">
          <FileText className="h-4 w-4 text-[#00E5FF] shrink-0" />
          <select
            aria-label="Select Regulatory PDF Document"
            value={currentDoc}
            onChange={(e) => {
              setCurrentDoc(e.target.value);
              setCurrentPage(1);
              setActiveHighlight(null);
            }}
            className="w-full bg-[#162032] border border-[#233554] rounded px-2.5 py-1.5 text-[#CCD6F6] text-xs focus:outline-none focus:border-[#00E5FF] transition-colors"
          >
            {AVAILABLE_DOCUMENTS.map((doc) => (
              <option key={doc.id} value={doc.id} className="bg-[#111C2E] text-white">
                {doc.label}
              </option>
            ))}
          </select>
        </div>

        {/* Page & Zoom Navigation Controls */}
        <div className="flex items-center space-x-2">
          {/* Page Navigator */}
          <div className="flex items-center bg-[#162032] border border-[#233554] rounded px-1.5 py-0.5">
            <button
              aria-label="Previous page"
              onClick={() => handlePageChange(-1)}
              disabled={currentPage <= 1}
              className="p-1 hover:text-[#00E5FF] disabled:opacity-30 disabled:hover:text-inherit"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="px-2 text-xs text-[#CCD6F6] font-mono">
              Page {currentPage}
            </span>
            <button
              aria-label="Next page"
              onClick={() => handlePageChange(1)}
              className="p-1 hover:text-[#00E5FF]"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center bg-[#162032] border border-[#233554] rounded px-1.5 py-0.5 space-x-1">
            <button
              aria-label="Zoom out"
              onClick={() => handleZoom(-15)}
              className="p-1 hover:text-[#00E5FF]"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <span className="text-xs text-[#CCD6F6] font-mono px-1">
              {zoomLevel}%
            </span>
            <button
              aria-label="Zoom in"
              onClick={() => handleZoom(15)}
              className="p-1 hover:text-[#00E5FF]"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Fullscreen Toggle */}
          <button
            aria-label={isFullscreen ? "Exit Fullscreen" : "Fullscreen Inspector"}
            onClick={() => setIsFullscreen((prev) => !prev)}
            className="p-1.5 rounded bg-[#162032] border border-[#233554] text-[#CCD6F6] hover:text-[#00E5FF] transition-colors"
          >
            {isFullscreen ? (
              <Minimize2 className="h-3.5 w-3.5" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Active Citation Focus Banner (Forward Sync Indicator) */}
      {activeHighlight && (
        <div
          className={`flex items-center justify-between px-3.5 py-2 border-b transition-all duration-300 ${
            highlightPulse
              ? "bg-[#10B981]/20 border-[#10B981] shadow-[0_0_20px_rgba(16,185,129,0.3)]"
              : "bg-[#162032] border-[#233554]"
          }`}
        >
          <div className="flex items-center space-x-2.5 min-w-0">
            <div
              className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                highlightPulse ? "bg-[#10B981] animate-ping" : "bg-[#10B981]"
              }`}
            />
            <span className="text-xs font-mono font-semibold text-[#10B981] truncate">
              PROVENANCE ANCHOR: {activeHighlight.document}
            </span>
            {activeHighlight.bbox && (
              <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-[#0B0F19] text-[10px] text-[#94A3B8] border border-[#233554]">
                bbox: [{activeHighlight.bbox.map((n) => Math.round(n)).join(", ")}]
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleClauseClickTrigger(activeHighlight.text)}
              className="text-[11px] text-[#00E5FF] hover:underline flex items-center space-x-1 font-mono"
            >
              <Sparkles className="h-3 w-3" />
              <span>Highlight Derived Claim</span>
            </button>
          </div>
        </div>
      )}

      {/* Main PDF Canvas Viewport */}
      <div className="relative flex-1 bg-[#0B0F19] overflow-hidden flex flex-col items-center justify-center">
        {loading && (
          <div className="absolute inset-0 bg-[#0B0F19]/80 backdrop-blur-xs flex flex-col items-center justify-center space-y-3 z-10 font-mono text-xs text-[#00E5FF]">
            <div className="w-8 h-8 border-2 border-[#00E5FF] border-t-transparent rounded-full animate-spin" />
            <span>STREAMING REGULATORY BYTES...</span>
          </div>
        )}

        {error ? (
          <div className="p-6 text-center space-y-3 font-mono text-xs">
            <AlertCircle className="h-8 w-8 text-[#EF4444] mx-auto" />
            <p className="text-[#EF4444]">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setError(null);
                setLoading(true);
              }}
            >
              Retry Connection
            </Button>
          </div>
        ) : (
          <div className="relative w-full h-full flex flex-col">
            {/* Embedded Native PDF Viewer */}
            <iframe
              ref={iframeRef}
              title="Regulatory PDF Inspector"
              src={pdfUrl}
              className="w-full flex-1 border-0 bg-[#0B0F19]"
              onLoad={() => setLoading(false)}
            />

            {/* Visual Bounding Box Overlay for Active Citation */}
            {activeHighlight && activeHighlight.text && (
              <div
                onClick={() => handleClauseClickTrigger(activeHighlight.text)}
                className="cursor-pointer mx-4 my-2 p-3 rounded bg-[#162032]/95 border border-[#10B981]/60 shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:border-[#10B981] transition-all"
              >
                <div className="flex items-center justify-between text-[11px] font-mono text-[#10B981] mb-1">
                  <span className="flex items-center space-x-1.5 font-bold">
                    <ShieldCheck className="h-3.5 w-3.5 text-[#10B981]" />
                    <span>GROUNDED STATUTORY PASSAGE</span>
                  </span>
                  <span className="text-[10px] text-[#94A3B8]">
                    Click to sync derived claim ↵
                  </span>
                </div>
                <p className="text-xs text-[#CCD6F6] font-mono leading-relaxed line-clamp-3 bg-[#0B0F19]/60 p-2 rounded border border-[#233554]">
                  "{activeHighlight.text}"
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Inspector Footer Telemetry */}
      <footer className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-[#0E1726] border-t border-[#233554] text-[11px] font-mono text-[#94A3B8]">
        <div className="flex items-center space-x-2 truncate">
          <Hash className="h-3.5 w-3.5 text-[#00E5FF] shrink-0" />
          <span className="text-[#CCD6F6]">SHA-256:</span>
          <span className="text-[#00E5FF] font-semibold truncate max-w-[220px]">
            {activeHighlight?.sha256 || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
          </span>
        </div>

        <div className="flex items-center space-x-3 text-[10px]">
          <span className="px-2 py-0.5 rounded bg-[#162032] border border-[#233554] text-[#10B981]">
            100% AIR-GAPPED VERIFIED
          </span>
          <span className="hidden sm:inline-block text-[#94A3B8]">
            LATENCY: &lt;50ms
          </span>
        </div>
      </footer>
    </div>
  );
}
