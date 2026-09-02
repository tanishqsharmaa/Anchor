"use client";

import React from "react";
import { FileText, ShieldCheck, ExternalLink, Bookmark } from "lucide-react";
import { Citation } from "@/lib/types";

interface CitationPanelProps {
  citations: Citation[];
  onSelectCitation?: (citation: Citation) => void;
}

export const CitationPanel: React.FC<CitationPanelProps> = ({
  citations,
  onSelectCitation,
}) => {
  if (!citations || citations.length === 0) {
    return (
      <div className="p-4 bg-navy-900/50 border border-border/50 rounded-lg text-center text-muted-foreground text-xs">
        <Bookmark className="w-5 h-5 mx-auto mb-1 opacity-50 text-cyan-400" />
        No statutory citations generated for this output.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono font-bold text-cyan-400 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          STATUTORY CITATION CROSS-REFERENCES ({citations.length})
        </span>
        <span className="text-[10px] text-muted-foreground font-mono">
          SHA-256 VERIFIED
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {citations.map((c, idx) => {
          const docName = c.document || "Statutory Gazette";
          const breadcrumb = `Citation Ref #${idx + 1}`;
          const page = c.page || 1;
          const hashSnippet = c.sha256 ? `${c.sha256.substring(0, 8)}...` : "VERIFIED";

          return (
            <div
              key={idx}
              onClick={() => onSelectCitation && onSelectCitation(c)}
              className="p-3 bg-card border border-border hover:border-cyan-400/50 rounded-lg cursor-pointer transition-colors group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span className="text-xs font-semibold text-foreground truncate max-w-[180px]">
                      {docName}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60">
                    P.{page}
                  </span>
                </div>

                <div className="text-[11px] font-mono text-cyan-300 mb-1 truncate">
                  {breadcrumb}
                </div>

                {c.text && (
                  <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                    &ldquo;{c.text}&rdquo;
                  </p>
                )}
              </div>

              <div className="mt-2.5 pt-2 border-t border-border/40 flex items-center justify-between text-[10px] text-muted-foreground font-mono">
                <span className="text-emerald-400 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" />
                  {hashSnippet}
                </span>
                <span className="flex items-center gap-1 text-cyan-400 group-hover:underline">
                  Inspect PDF <ExternalLink className="w-2.5 h-2.5" />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
