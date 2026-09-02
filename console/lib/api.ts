/**
 * api.ts — Typed Backend API Client for Tactical Console
 * Strictly handles sovereign local communication with FastAPI backend.
 */

import {
  HealthResponse,
  ReadyResponse,
  QueryRequest,
  PipelineEvent,
  DeckRequest,
  DeckResponse,
  EvalResponse,
  EvalRunResponse,
} from "./types";


export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const pin =
    process.env.NEXT_PUBLIC_SESSION_PIN ||
    (typeof window !== "undefined" ? localStorage.getItem("anchor_session_pin") : null);
  if (pin) {
    headers["X-Session-PIN"] = pin;
  }
  return headers;
}

/**
 * Liveness probe: checks backend status and loaded OpenVINO models.
 */
export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`, {
    method: "GET",
    headers: { Accept: "application/json", ...getAuthHeaders() },
    signal,
  });
  if (!response.ok) {
    throw new Error(`Health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Readiness probe: checks index statuses across LanceDB, Tantivy, and SQLite.
 */
export async function fetchReady(signal?: AbortSignal): Promise<ReadyResponse> {
  const response = await fetch(`${API_BASE}/ready`, {
    method: "GET",
    headers: { Accept: "application/json", ...getAuthHeaders() },
    signal,
  });
  if (!response.ok) {
    throw new Error(`Readiness check failed: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Streaming query execution over Server-Sent Events (SSE).
 * Parses `data: {...}` lines chunk-by-chunk in real time.
 */
export async function fetchQuerySSE(
  req: QueryRequest,
  onEvent: (event: PipelineEvent) => void,
  onError: (err: Error) => void,
  onComplete: () => void,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ question: req.question, stream: true }),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error");
      throw new Error(`Query failed [HTTP ${response.status}]: ${errorText}`);
    }

    if (!response.body) {
      throw new Error("Response body is not readable for SSE streaming.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // keep incomplete trailing chunk

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith(":") || trimmed.startsWith("event:")) {
          continue;
        }

        if (trimmed.startsWith("data:")) {
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const parsedEvent = JSON.parse(jsonStr) as PipelineEvent;
            onEvent(parsedEvent);
          } catch {
            // Non-JSON or partial chunk — log silently and proceed
          }
        }
      }
    }

    // Flush any remaining buffer
    if (buffer.trim().startsWith("data:")) {
      const jsonStr = buffer.trim().slice(5).trim();
      try {
        const parsedEvent = JSON.parse(jsonStr) as PipelineEvent;
        onEvent(parsedEvent);
      } catch {
        // ignore incomplete tail
      }
    }

    onComplete();
  } catch (err: unknown) {
    if (signal?.aborted) {
      return;
    }
    const errorObj = err instanceof Error ? err : new Error(String(err));
    onError(errorObj);
  }
}

/**
 * AutoDeck: Request presentation generation.
 */
export async function generateDeck(
  req: DeckRequest,
  signal?: AbortSignal
): Promise<DeckResponse> {
  const response = await fetch(`${API_BASE}/deck`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(req),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`Deck generation failed [HTTP ${response.status}]: ${errorText}`);
  }

  return response.json();
}

/**
 * Return download URL for a generated PPTX deck.
 */
export function getDeckDownloadUrl(deckId: string): string {
  return `${API_BASE}/deck/${encodeURIComponent(deckId)}/download`;
}

/**
 * Return direct static URL for regulatory PDF viewer.
 */
export function getPdfUrl(docName: string): string {
  return `${API_BASE}/pdf/${encodeURIComponent(docName)}`;
}

/**
 * Fetch latest statutory evaluation metrics and system telemetry.
 */
export async function fetchEval(signal?: AbortSignal): Promise<EvalResponse> {
  const response = await fetch(`${API_BASE}/eval`, {
    method: "GET",
    headers: { Accept: "application/json", ...getAuthHeaders() },
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`Failed to fetch evaluation metrics [HTTP ${response.status}]: ${errorText}`);
  }

  return response.json();
}

/**
 * Trigger full benchmark evaluation run and quality gate assessment.
 */
export async function runEvalBenchmark(signal?: AbortSignal): Promise<EvalRunResponse> {
  const response = await fetch(`${API_BASE}/eval/run`, {
    method: "POST",
    headers: { Accept: "application/json", ...getAuthHeaders() },
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`Failed to run evaluation benchmark [HTTP ${response.status}]: ${errorText}`);
  }

  return response.json();
}

