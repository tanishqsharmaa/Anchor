import React from "react";
import { Citation } from "@/lib/types";

interface CitationBadgeProps {
  citation: Citation;
  index?: number;
  onClick?: (citation: Citation) => void;
  active?: boolean;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citation,
  index,
  onClick,
  active = false,
}) => {
  const shortHash = citation.sha256 ? `${citation.sha256.slice(0, 7)}...` : "";

  return (
    <button
      type="button"
      onClick={() => onClick?.(citation)}
      className={`inline-flex items-center space-x-2 px-2.5 py-1 rounded border text-xs font-mono transition-all duration-150 text-left ${
        active
          ? "bg-[#00E5FF]/20 border-[#00E5FF] text-[#00E5FF] shadow-[0_0_10px_rgba(0,229,255,0.3)]"
          : "bg-[#162032] border-[#233554] text-[#CCD6F6] hover:border-[#00E5FF]/60 hover:text-white"
      }`}
      title={citation.text || `Page ${citation.page} in ${citation.document}`}
    >
      <span className="text-[#FFD700] font-semibold">
        {typeof index === "number" ? `[${index + 1}]` : "§"}
      </span>
      <span className="truncate max-w-[180px] font-medium">
        {citation.document || "Document"}
      </span>
      <span className="text-[#94A3B8]">p.{citation.page}</span>
      {shortHash && (
        <span className="text-[#10B981] text-[10px] bg-[#10B981]/10 px-1 py-0.5 rounded border border-[#10B981]/20">
          SHA:{shortHash}
        </span>
      )}
    </button>
  );
};
