"use client";

/**
 * SSEConsole.tsx — Real-Time C4ISR Pipeline Telemetry & Token Streaming Console
 * Displays step-by-step pipeline execution, latencies, and token-by-token generation.
 */

import React, { useEffect, useRef, useState } from "react";
import {
  Activity,
  Terminal,
  Clock,
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Pause,
  Play,
  RotateCcw,
} from "lucide-react";
import { UseQueryResult } from "@/hooks/useQuery";
import { PipelineStage, StageTelemetry } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface SSEConsoleProps {
  query: UseQueryResult;
  className?: string;
}

const STAGE_ICONS: Record<PipelineStage, React.ReactNode> = {
  classify: <Layers className="h-3.5 w-3.5" />,
  retrieve: <Cpu className="h-3.5 w-3.5" />,
  rerank: <Activity className="h-3.5 w-3.5" />,
  gate: <AlertTriangle className="h-3.5 w-3.5" />,
  generate: <Terminal className="h-3.5 w-3.5" />,
  verify: <CheckCircle2 className="h-3.5 w-3.5" />,
  abstain: <AlertTriangle className="h-3.5 w-3.5" />,
  resolve: <CheckCircle2 className="h-3.5 w-3.5" />,
  complete: <CheckCircle2 className="h-3.5 w-3.5" />,
  error: <AlertTriangle className="h-3.5 w-3.5" />,
};

export const SSEConsole: React.FC<SSEConsoleProps> = ({ query, className = "" }) => {

  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const {
    status,
    stages,
    activeStage,
    answer,
    rawEvents,
    ttftMs,
    totalLatencyMs,
    resetQuery,
  } = query;

  // Auto-scroll terminal when new tokens or events arrive
  useEffect(() => {
    if (autoScroll) {
      terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [answer, rawEvents, autoScroll]);

  const getStageStatusBadge = (stage: StageTelemetry) => {
    switch (stage.status) {
      case "completed":
        return <Badge variant="green">PASS</Badge>;
      case "running":
        return (
          <Badge variant="cyan" dot>
            EXEC
          </Badge>
        );
      case "warning":
        return <Badge variant="amber">WARN</Badge>;
      case "error":
        return <Badge variant="red">FAIL</Badge>;
      default:
        return <Badge variant="slate">WAIT</Badge>;
    }
  };

  return (
    <div className={`flex flex-col h-full bg-[#111C2E] rounded-lg border border-[#233554] overflow-hidden ${className}`}>

      {/* Console Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#233554] bg-[#0E1726]">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded bg-[#00E5FF]/10 border border-[#00E5FF]/30 text-[#00E5FF]">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-wider text-white font-mono uppercase">
              C4ISR Telemetry & SSE Stream
            </h2>
            <p className="text-[11px] text-[#94A3B8]">
              Real-Time Chain-of-Thought & Inference Metrics
            </p>
          </div>
        </div>

        {/* Live Metrics Header Badges */}
        <div className="flex items-center space-x-3 text-xs font-mono">
          {ttftMs !== null && (
            <div className="flex items-center space-x-1 text-[#00E5FF] bg-[#00E5FF]/10 px-2 py-0.5 rounded border border-[#00E5FF]/30">
              <Clock className="h-3 w-3" />
              <span>TTFT: {ttftMs}ms</span>
            </div>
          )}
          {totalLatencyMs !== null && (
            <div className="flex items-center space-x-1 text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded border border-[#10B981]/30">
              <span>TOTAL: {totalLatencyMs}ms</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Console Split: Timeline Top (40%), Terminal Bottom (60%) */}
      <div className="flex-1 flex flex-col p-4 space-y-4 overflow-hidden">
        {/* Pipeline Stage Timeline */}
        <div className="bg-[#0B0F19] rounded-lg border border-[#233554] p-3.5 space-y-2">
          <div className="flex items-center justify-between border-b border-[#233554] pb-2 text-xs font-mono font-bold text-[#94A3B8] uppercase">
            <span>Pipeline Stage Progression</span>
            <span>Latency / Status</span>
          </div>

          <div className="grid grid-cols-1 gap-2 pt-1">
            {stages.map((stg, idx) => {
              const isActive = activeStage === stg.stage;
              return (
                <div
                  key={idx}
                  className={`flex items-center justify-between px-3 py-1.5 rounded border text-xs font-mono transition-colors ${
                    isActive
                      ? "bg-[#00E5FF]/10 border-[#00E5FF] text-white shadow-[0_0_10px_rgba(0,229,255,0.15)]"
                      : stg.status === "completed"
                      ? "bg-[#162032] border-[#233554] text-[#CCD6F6]"
                      : "bg-[#111C2E] border-[#1F2E47] text-[#64748B]"
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <span className={isActive ? "text-[#00E5FF]" : "text-[#94A3B8]"}>
                      {STAGE_ICONS[stg.stage] || <Activity className="h-3.5 w-3.5" />}
                    </span>
                    <span className="font-semibold uppercase tracking-wider">
                      {stg.stage}
                    </span>
                    {stg.summary && (
                      <span className="text-[11px] text-[#94A3B8] truncate max-w-[180px]">
                        — {stg.summary}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {stg.durationMs !== undefined && (
                      <span className="text-[11px] text-[#FFD700]">
                        {stg.durationMs.toFixed(1)}ms
                      </span>
                    )}
                    {getStageStatusBadge(stg)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Live Token Terminal */}
        <div className="flex-1 bg-[#0B0F19] rounded-lg border border-[#233554] flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-[#233554] bg-[#0E1726] text-xs font-mono text-[#94A3B8]">
            <div className="flex items-center space-x-2">
              <Terminal className="h-3.5 w-3.5 text-[#00E5FF]" />
              <span className="text-white font-bold tracking-wider uppercase">
                Raw Event Stream & Token Terminal
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setAutoScroll((prev) => !prev)}
                className="flex items-center space-x-1 px-2 py-0.5 rounded bg-[#162032] hover:text-white transition"
              >
                {autoScroll ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                <span>{autoScroll ? "Auto-scroll: ON" : "PAUSED"}</span>
              </button>
              <button
                type="button"
                onClick={resetQuery}
                className="p-1 rounded bg-[#162032] hover:text-white transition"
                title="Clear Console"
              >
                <RotateCcw className="h-3 w-3" />
              </button>
            </div>
          </div>

          <div className="flex-1 p-3.5 overflow-y-auto terminal-scroll font-mono text-xs text-[#CCD6F6] space-y-1.5">
            {rawEvents.length === 0 ? (
              <div className="text-[#64748B] italic">
                // Terminal standing by. Dispatch a query to observe live telemetry stream.
              </div>
            ) : (
              rawEvents.map((evt, idx) => (
                <div key={idx} className="leading-relaxed flex items-start space-x-2">
                  <span className="text-[#64748B] select-none text-[10px] shrink-0 pt-0.5">
                    {evt.timestamp?.slice(11, 19) || "00:00:00"}
                  </span>
                  <span className="text-[#00E5FF] font-bold shrink-0">
                    [{evt.stage.toUpperCase()}]
                  </span>
                  <span className="text-[#CCD6F6] break-all">
                    {evt.data?.token
                      ? `token: "${evt.data.token}"`
                      : evt.data?.sentence
                      ? `sentence: "${evt.data.sentence}" (score: ${evt.data.nli_score ?? "1.00"})`
                      : evt.data?.answer
                      ? `resolved: "${evt.data.answer}"`
                      : evt.data?.reason
                      ? `refusal: ${evt.data.reason}`
                      : JSON.stringify(evt.data)}
                  </span>
                </div>
              ))
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
};
