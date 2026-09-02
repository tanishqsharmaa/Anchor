/**
 * types.ts — Shared TypeScript Definitions for Tactical Console
 * Strictly aligned with Reference/ARCHITECTURE.md and Docs/API_CONTRACTS.md
 */

export type PipelineStage =
  | "classify"
  | "retrieve"
  | "rerank"
  | "gate"
  | "generate"
  | "verify"
  | "abstain"
  | "resolve"
  | "complete"
  | "error";

export type NLIStatus = "certified" | "regen" | "abstain";

export type QueryRouteType = "structured" | "interpretive";

export interface Citation {
  document: string;
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  byte_offset?: number;
  byte_length?: number;
  sha256: string;
  text: string;
}

export interface ChunkRef {
  id: string;
  document: string;
  breadcrumb: string;
  score: number;
  text_preview: string;
}

export interface StructuredCFAResult {
  schedule_no?: number;
  schedule_name?: string;
  tier?: string;
  tier_name?: string;
  with_ifa?: number | null;
  without_ifa?: number | null;
  pac_limit?: number | null;
  notes?: string | null;
  source_doc?: string;
  mode?: string;
  threshold?: number;
  threshold_text?: string;
}

export interface PipelineEventData {
  type?: QueryRouteType;
  entities?: Record<string, unknown>;
  chunks?: number;
  top_chunks?: ChunkRef[];
  relevant?: boolean;
  token?: string;
  sentence?: string;
  nli_score?: number;
  status?: NLIStatus;
  answer?: string;
  citations?: Citation[];
  reason?: string;
  explanation?: string;
  remedy_suggestions?: string[];
  error?: string;
  latency_ms?: number;
  resolved_table?: StructuredCFAResult;
}

export interface PipelineEvent {
  stage: PipelineStage;
  data: PipelineEventData;
  timestamp: string;
}

export interface QueryRequest {
  question: string;
  stream?: boolean;
}

export interface VerifiedSentence {
  text: string;
  nliScore?: number;
  status?: NLIStatus;
  citationIndices?: number[];
}

export interface StageTelemetry {
  stage: PipelineStage;
  status: "pending" | "running" | "completed" | "warning" | "error";
  durationMs?: number;
  summary?: string;
  details?: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  version: string;
  models_loaded: string[];
  ollama_available: boolean;
}

export interface ReadyResponse {
  ready: boolean;
  chunks_indexed: number;
  schedules_loaded: number;
  stores: {
    lancedb: boolean;
    tantivy: boolean;
    sqlite: boolean;
  };
}

export interface DeckRequest {
  topic: string;
  context?: string;
  num_slides?: number;
}

export interface SlideASTItem {
  id?: string;
  type: "HERO_SLIDE" | "BLUF_EXECUTIVE" | "POLICY_MATRIX" | "FINANCIAL_DELEGATION" | string;
  title: string;
  classification: string;
  dtg?: string;
  officer?: string;
  unit?: string;
  decision_requested?: string;
  who?: string;
  what?: string;
  when?: string;
  where?: string;
  why?: string;
  urgency?: string;
  schedule?: number | string;
  schedule_name?: string;
  tier?: string;
  tier_name?: string;
  mode?: string;
  ifa_required?: boolean;
  with_ifa?: number | null;
  without_ifa?: number | null;
  total_estimate_cr?: number | null;
  budget_head?: string;
  indigenisation_pct?: number | null;
  milestones?: Array<{ phase: string; description: string; target_date?: string; payment_pct?: number }>;
  nli_scores?: number[];
  verified?: boolean;
  [key: string]: unknown;
}

export interface DeckResponse {
  success: boolean;
  data: {
    deck_id: string;
    title: string;
    ast: {
      slides: SlideASTItem[];
    };
    html_slides: string[];
    pptx_url: string;
    verification_report: {
      all_claims_verified: boolean;
      lowest_nli_score: number;
    };
    generation_time_ms: number;
  };
}

export interface EvalMetricsData {
  faithfulness: number;
  citation_precision: number;
  context_recall: number;
  hallucination_rate: number;
  abstention_accuracy: number;
  structured_accuracy: number;
  p95_slide_latency_ms: number;
  sse_first_token_ms: number;
  peak_ram_gb: number;
}

export interface EvalResponse {
  success: boolean;
  data: EvalMetricsData;
}

export interface EvalRunResponse {
  success: boolean;
  data: {
    passed: boolean;
    total_questions: number;
    metrics: Record<string, number>;
    thresholds: Record<string, number>;
    failed_metrics: string[];
    execution_time_seconds: number;
  };
}

export interface PDFInspectorProps {
  selectedCitation?: Citation | null;
  onClauseClick?: (clauseText: string, citation: Citation) => void;
  className?: string;
}

export interface SlidePreviewProps {
  slide: SlideASTItem;
  slideIndex: number;
  totalSlides: number;
  className?: string;
}

export interface SlideStudioProps {
  isOpen: boolean;
  onClose: () => void;
  initialTopic?: string;
  onDownloadPPTX?: (deckId: string) => void;
}

export interface EvalDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

