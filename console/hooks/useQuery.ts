"use client";

/**
 * useQuery.ts — High-Level Query Management Hook
 * Connects QueryPanel and SSEConsole with real-time state, token accumulation, and telemetry.
 */

import { useState, useCallback, useRef } from "react";
import {
  PipelineEvent,
  PipelineStage,
  Citation,
  ChunkRef,
  StructuredCFAResult,
  VerifiedSentence,
  StageTelemetry,
  QueryRouteType,
} from "@/lib/types";
import { fetchQuerySSE } from "@/lib/api";

export type QueryExecutionStatus =
  | "idle"
  | "submitting"
  | "streaming"
  | "completed"
  | "abstained"
  | "error";

export interface UseQueryResult {
  status: QueryExecutionStatus;
  question: string;
  answer: string;
  routeType: QueryRouteType | null;
  citations: Citation[];
  verifiedSentences: VerifiedSentence[];
  structuredResult: StructuredCFAResult | null;
  topChunks: ChunkRef[];
  stages: StageTelemetry[];
  activeStage: PipelineStage | null;
  ttftMs: number | null;
  totalLatencyMs: number | null;
  refusalReason: string | null;
  refusalExplanation: string | null;
  remedySuggestions: string[];
  errorMessage: string | null;
  rawEvents: PipelineEvent[];
  submitQuery: (question: string) => Promise<void>;
  cancelQuery: () => void;
  resetQuery: () => void;
}

const INITIAL_STAGES: StageTelemetry[] = [
  { stage: "classify", status: "pending", summary: "Query Classification" },
  { stage: "retrieve", status: "pending", summary: "Dense + Sparse Retrieval" },
  { stage: "rerank", status: "pending", summary: "Cross-Encoder Reranking" },
  { stage: "gate", status: "pending", summary: "Corrective Relevance Gate" },
  { stage: "generate", status: "pending", summary: "Constrained LLM Synthesis" },
  { stage: "verify", status: "pending", summary: "Per-Sentence NLI Gate" },
];

export function useQuery(): UseQueryResult {
  const [status, setStatus] = useState<QueryExecutionStatus>("idle");
  const [question, setQuestion] = useState<string>("");
  const [answer, setAnswer] = useState<string>("");
  const [routeType, setRouteType] = useState<QueryRouteType | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [verifiedSentences, setVerifiedSentences] = useState<VerifiedSentence[]>([]);
  const [structuredResult, setStructuredResult] = useState<StructuredCFAResult | null>(null);
  const [topChunks, setTopChunks] = useState<ChunkRef[]>([]);
  const [stages, setStages] = useState<StageTelemetry[]>(INITIAL_STAGES);
  const [activeStage, setActiveStage] = useState<PipelineStage | null>(null);
  const [ttftMs, setTtftMs] = useState<number | null>(null);
  const [totalLatencyMs, setTotalLatencyMs] = useState<number | null>(null);
  const [refusalReason, setRefusalReason] = useState<string | null>(null);
  const [refusalExplanation, setRefusalExplanation] = useState<string | null>(null);
  const [remedySuggestions, setRemedySuggestions] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [rawEvents, setRawEvents] = useState<PipelineEvent[]>([]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const startTimeRef = useRef<number>(0);
  const ttftRecordedRef = useRef<boolean>(false);

  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStatus((prev) => (prev === "streaming" ? "completed" : prev));
  }, []);

  const resetQuery = useCallback(() => {
    cancelQuery();
    setStatus("idle");
    setQuestion("");
    setAnswer("");
    setRouteType(null);
    setCitations([]);
    setVerifiedSentences([]);
    setStructuredResult(null);
    setTopChunks([]);
    setStages(INITIAL_STAGES);
    setActiveStage(null);
    setTtftMs(null);
    setTotalLatencyMs(null);
    setRefusalReason(null);
    setRefusalExplanation(null);
    setRemedySuggestions([]);
    setErrorMessage(null);
    setRawEvents([]);
  }, [cancelQuery]);

  const updateStage = useCallback(
    (
      stageName: PipelineStage,
      stageStatus: StageTelemetry["status"],
      summary?: string,
      details?: Record<string, unknown>,
      durationMs?: number
    ) => {
      setStages((prev) => {
        const existingIdx = prev.findIndex((s) => s.stage === stageName);
        if (existingIdx >= 0) {
          const next = [...prev];
          next[existingIdx] = {
            ...next[existingIdx],
            status: stageStatus,
            summary: summary || next[existingIdx].summary,
            details: details || next[existingIdx].details,
            durationMs: durationMs ?? next[existingIdx].durationMs,
          };
          return next;
        }
        return [
          ...prev,
          {
            stage: stageName,
            status: stageStatus,
            summary: summary || stageName,
            details,
            durationMs,
          },
        ];
      });
    },
    []
  );

  const submitQuery = useCallback(
    async (queryText: string) => {
      const trimmed = queryText.trim();
      if (!trimmed) return;

      resetQuery();
      setQuestion(trimmed);
      setStatus("submitting");
      startTimeRef.current = performance.now();
      ttftRecordedRef.current = false;

      const controller = new AbortController();
      abortControllerRef.current = controller;

      await fetchQuerySSE(
        { question: trimmed, stream: true },
        (event: PipelineEvent) => {
          setRawEvents((prev) => [...prev, event]);
          setActiveStage(event.stage);

          // Measure TTFT on first token / answer
          if (!ttftRecordedRef.current) {
            if (event.data?.token || event.stage === "generate" || event.stage === "resolve") {
              const elapsed = performance.now() - startTimeRef.current;
              setTtftMs(Math.round(elapsed));
              ttftRecordedRef.current = true;
            }
          }

          switch (event.stage) {
            case "classify": {
              setStatus("streaming");
              const qType = event.data.type || "interpretive";
              setRouteType(qType);
              updateStage(
                "classify",
                "completed",
                `Classified: ${qType.toUpperCase()} Path`,
                { entities: event.data.entities },
                event.data.latency_ms
              );
              break;
            }

            case "resolve": {
              setStatus("streaming");
              if (event.data.answer) {
                setAnswer(event.data.answer);
              }
              if (event.data.citations) {
                setCitations(event.data.citations);
              }
              if (event.data.resolved_table || event.data.entities) {
                const tableData = event.data.resolved_table || (event.data.entities as unknown as StructuredCFAResult);
                setStructuredResult(tableData);
              }
              updateStage(
                "classify",
                "completed",
                "Path A: Deterministic SQL Resolved",
                { answer: event.data.answer },
                event.data.latency_ms
              );
              break;
            }

            case "retrieve": {
              if (typeof event.data.chunks === "number") {
                updateStage(
                  "retrieve",
                  "completed",
                  `Retrieved ${event.data.chunks} chunks via RRF`,
                  undefined,
                  event.data.latency_ms
                );
              }
              break;
            }

            case "rerank": {
              if (event.data.top_chunks) {
                setTopChunks(event.data.top_chunks);
                updateStage(
                  "rerank",
                  "completed",
                  `Reranked top-${event.data.top_chunks.length} chunks`,
                  { top_chunks: event.data.top_chunks },
                  event.data.latency_ms
                );
              }
              break;
            }

            case "gate": {
              const passed = event.data.relevant ?? true;
              updateStage(
                "gate",
                passed ? "completed" : "warning",
                passed ? "Corrective Gate: PASSED" : "Corrective Gate: REJECTED",
                undefined,
                event.data.latency_ms
              );
              break;
            }

            case "generate": {
              if (event.data.token) {
                setAnswer((prev) => prev + event.data.token);
              }
              updateStage("generate", "running", "Synthesizing constrained response...");
              break;
            }

            case "verify": {
              updateStage("generate", "completed", "Synthesis Complete");
              if (event.data.sentence) {
                const newSentence: VerifiedSentence = {
                  text: event.data.sentence,
                  nliScore: event.data.nli_score,
                  status: event.data.status || "certified",
                };
                setVerifiedSentences((prev) => [...prev, newSentence]);
              }
              updateStage(
                "verify",
                event.data.status === "abstain" ? "warning" : "completed",
                `NLI Gate: ${event.data.status?.toUpperCase()} (${(
                  (event.data.nli_score ?? 1.0) * 100
                ).toFixed(1)}%)`,
                undefined,
                event.data.latency_ms
              );
              break;
            }

            case "complete": {
              if (event.data.answer) {
                setAnswer(event.data.answer);
              }
              if (event.data.citations) {
                setCitations(event.data.citations);
              }
              if (event.data.latency_ms) {
                setTotalLatencyMs(Math.round(event.data.latency_ms));
              }
              setStatus("completed");
              break;
            }

            case "abstain": {
              setStatus("abstained");
              setRefusalReason(event.data.reason || "OUT_OF_DOMAIN");
              setRefusalExplanation(
                event.data.explanation ||
                  "No verified statutory authority or regulatory clause exists in the active corpus to substantiate an answer."
              );
              if (event.data.remedy_suggestions) {
                setRemedySuggestions(event.data.remedy_suggestions);
              }
              updateStage("verify", "warning", `Certified Abstention: ${event.data.reason}`);
              break;
            }

            case "error": {
              setStatus("error");
              setErrorMessage(event.data.error || "An unexpected pipeline error occurred.");
              break;
            }
          }
        },
        (err) => {
          setStatus("error");
          setErrorMessage(err.message || "Failed to execute streaming query.");
        },
        () => {
          const totalElapsed = performance.now() - startTimeRef.current;
          setTotalLatencyMs((prev) => prev ?? Math.round(totalElapsed));
          setStatus((prev) => (prev === "streaming" || prev === "submitting" ? "completed" : prev));
        },
        controller.signal
      );
    },
    [resetQuery, updateStage]
  );

  return {
    status,
    question,
    answer,
    routeType,
    citations,
    verifiedSentences,
    structuredResult,
    topChunks,
    stages,
    activeStage,
    ttftMs,
    totalLatencyMs,
    refusalReason,
    refusalExplanation,
    remedySuggestions,
    errorMessage,
    rawEvents,
    submitQuery,
    cancelQuery,
    resetQuery,
  };
}
