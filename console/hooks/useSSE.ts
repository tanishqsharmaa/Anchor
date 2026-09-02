"use client";

/**
 * useSSE.ts — React Hook for SSE Event Streaming
 * Handles stream connection, abort controller, and event dispatch.
 */

import { useState, useCallback, useRef } from "react";
import { PipelineEvent } from "@/lib/types";
import { fetchQuerySSE } from "@/lib/api";

export interface UseSSEResult {
  events: PipelineEvent[];
  isStreaming: boolean;
  error: Error | null;
  ttftMs: number | null;
  totalDurationMs: number | null;
  startStream: (question: string, onEventCallback?: (event: PipelineEvent) => void) => Promise<void>;
  cancelStream: () => void;
  clearEvents: () => void;
}

export function useSSE(): UseSSEResult {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [ttftMs, setTtftMs] = useState<number | null>(null);
  const [totalDurationMs, setTotalDurationMs] = useState<number | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const startTimeRef = useRef<number>(0);
  const firstTokenRecordedRef = useRef<boolean>(false);

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const clearEvents = useCallback(() => {
    cancelStream();
    setEvents([]);
    setError(null);
    setTtftMs(null);
    setTotalDurationMs(null);
  }, [cancelStream]);

  const startStream = useCallback(
    async (question: string, onEventCallback?: (event: PipelineEvent) => void) => {
      cancelStream();

      setEvents([]);
      setError(null);
      setTtftMs(null);
      setTotalDurationMs(null);
      setIsStreaming(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;
      startTimeRef.current = performance.now();
      firstTokenRecordedRef.current = false;

      await fetchQuerySSE(
        { question, stream: true },
        (event) => {
          // Record Time-to-First-Token if this is the first token or answer event
          if (!firstTokenRecordedRef.current) {
            if (event.data?.token || event.stage === "generate" || event.stage === "resolve") {
              const elapsed = performance.now() - startTimeRef.current;
              setTtftMs(Math.round(elapsed));
              firstTokenRecordedRef.current = true;
            }
          }

          setEvents((prev) => [...prev, event]);
          if (onEventCallback) {
            onEventCallback(event);
          }
        },
        (err) => {
          setError(err);
          setIsStreaming(false);
        },
        () => {
          const totalElapsed = performance.now() - startTimeRef.current;
          setTotalDurationMs(Math.round(totalElapsed));
          setIsStreaming(false);
        },
        controller.signal
      );
    },
    [cancelStream]
  );

  return {
    events,
    isStreaming,
    error,
    ttftMs,
    totalDurationMs,
    startStream,
    cancelStream,
    clearEvents,
  };
}
