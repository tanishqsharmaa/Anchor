"use client";

/**
 * useDeck.ts — Presentation Generation & AST Slide Management Hook
 * Strictly coordinates with AutoDeck AI backend (/deck and /deck/{id}/download).
 */

import { useState, useCallback, useRef } from "react";
import { generateDeck, getDeckDownloadUrl } from "@/lib/api";
import { DeckResponse, SlideASTItem } from "@/lib/types";

export type DeckStatus = "idle" | "generating" | "ready" | "error";

export interface UseDeckReturn {
  status: DeckStatus;
  deck: DeckResponse["data"] | null;
  slides: SlideASTItem[];
  activeSlideIndex: number;
  error: string | null;
  generationTimeMs: number;
  verificationReport: {
    all_claims_verified: boolean;
    lowest_nli_score: number;
  } | null;
  generate: (topic: string, context?: string, numSlides?: number) => Promise<void>;
  reorderSlides: (oldIndex: number, newIndex: number) => void;
  setActiveSlideIndex: (index: number) => void;
  downloadPPTX: () => void;
  reset: () => void;
}

export function useDeck(): UseDeckReturn {
  const [status, setStatus] = useState<DeckStatus>("idle");
  const [deck, setDeck] = useState<DeckResponse["data"] | null>(null);
  const [slides, setSlides] = useState<SlideASTItem[]>([]);
  const [activeSlideIndex, setActiveSlideIndex] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [generationTimeMs, setGenerationTimeMs] = useState<number>(0);
  const [verificationReport, setVerificationReport] = useState<{
    all_claims_verified: boolean;
    lowest_nli_score: number;
  } | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const generate = useCallback(
    async (topic: string, context?: string, numSlides: number = 6) => {
      if (!topic.trim()) {
        setError("Please enter a valid presentation topic.");
        return;
      }

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      setStatus("generating");
      setError(null);

      const startTime = performance.now();

      try {
        const response = await generateDeck(
          {
            topic: topic.trim(),
            context: context?.trim(),
            num_slides: numSlides,
          },
          abortControllerRef.current.signal
        );

        if (response.success && response.data) {
          const duration = Math.round(performance.now() - startTime);
          setDeck(response.data);
          const rawSlides = response.data.ast?.slides || [];
          const indexedSlides = rawSlides.map((slide, idx) => ({
            ...slide,
            id: slide.id || `slide-${idx + 1}`,
          }));
          setSlides(indexedSlides);
          setActiveSlideIndex(0);
          setGenerationTimeMs(response.data.generation_time_ms || duration);
          setVerificationReport(response.data.verification_report || null);
          setStatus("ready");
        } else {
          throw new Error("Invalid response received from AutoDeck engine.");
        }
      } catch (err: unknown) {
        if (abortControllerRef.current?.signal.aborted) {
          return;
        }
        const errorMsg = err instanceof Error ? err.message : "Deck generation failed.";
        setError(errorMsg);
        setStatus("error");
      }
    },
    []
  );

  const reorderSlides = useCallback((oldIndex: number, newIndex: number) => {
    setSlides((prev) => {
      if (
        oldIndex < 0 ||
        oldIndex >= prev.length ||
        newIndex < 0 ||
        newIndex >= prev.length ||
        oldIndex === newIndex
      ) {
        return prev;
      }
      const updated = [...prev];
      const [movedItem] = updated.splice(oldIndex, 1);
      updated.splice(newIndex, 0, movedItem);
      return updated;
    });
  }, []);

  const downloadPPTX = useCallback(() => {
    if (!deck?.deck_id) {
      return;
    }
    const downloadUrl = getDeckDownloadUrl(deck.deck_id);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `${deck.deck_id}.pptx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [deck]);

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStatus("idle");
    setDeck(null);
    setSlides([]);
    setActiveSlideIndex(0);
    setError(null);
    setGenerationTimeMs(0);
    setVerificationReport(null);
  }, []);

  return {
    status,
    deck,
    slides,
    activeSlideIndex,
    error,
    generationTimeMs,
    verificationReport,
    generate,
    reorderSlides,
    setActiveSlideIndex,
    downloadPPTX,
    reset,
  };
}
