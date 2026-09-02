"""
routes_query.py — Full Server-Sent Events (SSE) Streaming Query Endpoint with Defense Audit Logging
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, AsyncGenerator, Optional, Union
import uuid
from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from anchor.generate.abstention import CertifiedAbstention, RefusalReasonCode
from anchor.generate.citation import Citation, CitationAnchorer
from anchor.generate.nli_gate import NLIGate
from anchor.generate.synthesizer import Synthesizer
from anchor.retrieve.classifier import QuestionClassifier
from anchor.retrieve.corrective_gate import CorrectiveGate
from anchor.retrieve.hybrid import HybridRetriever, RetrievedChunk
from anchor.retrieve.reranker import Reranker
from anchor.retrieve.resolver import (
    resolve_dfpds_delegation,
    resolve_dfpds_comparison,
    resolve_dpm_threshold,
)
from anchor.trust.audit import AuditLogger, audit_logger

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])


class QueryRequest(BaseModel):
    """Incoming query request payload."""

    question: str = Field(..., min_length=3, max_length=2000, description="Natural language regulatory question")
    stream: bool = Field(default=True, description="Whether to stream pipeline telemetry via Server-Sent Events")
    query_id: Optional[str] = Field(default=None, description="Optional custom query identifier")


class PipelineEventData(BaseModel):
    """Data payload for typed pipeline events."""

    query_id: Optional[str] = None
    type: Optional[str] = None
    entities: Optional[dict[str, Any]] = None
    chunks: Optional[int] = None
    top_chunks: Optional[list[dict[str, Any]]] = None
    relevant: Optional[bool] = None
    token: Optional[str] = None
    sentence: Optional[str] = None
    nli_score: Optional[float] = None
    status: Optional[str] = None
    answer: Optional[str] = None
    citations: Optional[list[dict[str, Any]]] = None
    reason: Optional[str] = None
    explanation: Optional[str] = None
    remedy_suggestions: Optional[list[str]] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None


class PipelineEvent(BaseModel):
    """
    Standard Server-Sent Event conforming to Reference/ARCHITECTURE.md:L476-495.
    """

    stage: str
    data: PipelineEventData
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class QueryPipelineOrchestrator:
    """
    Orchestrates dual-path query processing across all retrieval, synthesis, verification,
    and citation anchoring stages, recording immutable defense audit trails.
    """

    def __init__(
        self,
        classifier: Optional[QuestionClassifier] = None,
        hybrid: Optional[HybridRetriever] = None,
        reranker: Optional[Reranker] = None,
        gate: Optional[CorrectiveGate] = None,
        synthesizer: Optional[Synthesizer] = None,
        nli_gate: Optional[NLIGate] = None,
        anchorer: Optional[CitationAnchorer] = None,
        abstention: Optional[CertifiedAbstention] = None,
        audit: Optional[AuditLogger] = None,
    ) -> None:
        self.classifier = classifier or QuestionClassifier()
        self.hybrid = hybrid or HybridRetriever()
        self.reranker = reranker or Reranker()
        self.gate = gate or CorrectiveGate()
        self.synthesizer = synthesizer or Synthesizer()
        self.nli_gate = nli_gate or NLIGate()
        self.anchorer = anchorer or CitationAnchorer()
        self.abstention = abstention or CertifiedAbstention()
        self.audit = audit or audit_logger

    def _make_event(self, stage: str, data: dict[str, Any]) -> str:
        """Serialize a stage payload into a standardized JSON string for SSE transmission."""
        event = PipelineEvent(
            stage=stage,
            data=PipelineEventData.model_validate(data),
        )
        return event.model_dump_json()

    async def execute_stream(
        self,
        question: str,
        query_id: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> AsyncGenerator[dict[str, str], None]:
        """
        Execute full dual-path query pipeline, yield SSE events, and commit audit record.
        Includes client disconnect detection (ENH-004) and multi-schedule comparative routing (ENH-002).
        """
        start_time = time.perf_counter()
        q_clean = question.strip()
        q_id = query_id or f"q_{uuid.uuid4().hex[:12]}"

        try:
            # 1. CLASSIFY STAGE
            t0 = time.perf_counter()
            cls_result = self.classifier.classify(q_clean)
            classify_latency = round((time.perf_counter() - t0) * 1000.0, 2)

            yield {
                "event": "message",
                "data": self._make_event(
                    stage="classify",
                    data={
                        "query_id": q_id,
                        "type": cls_result.query_type,
                        "entities": {
                            "schedule_no": cls_result.schedule_no,
                            "schedule_nos": cls_result.schedule_nos,
                            "tier": cls_result.tier,
                            "with_ifa": cls_result.with_ifa,
                            "is_pac": cls_result.is_pac,
                            "dpm_mode": cls_result.dpm_mode,
                        },
                        "latency_ms": classify_latency,
                    },
                ),
            }

            # =========================================================================
            # PATH A: DETERMINISTIC STRUCTURED QUERY & COMPARATIVE RESOLUTION
            # =========================================================================
            # Case A1: Multi-Schedule Comparative Resolution (ENH-002)
            if (
                cls_result.query_type == "structured"
                and len(cls_result.schedule_nos) > 1
                and cls_result.tier is not None
            ):
                t0 = time.perf_counter()
                comp_res = resolve_dfpds_comparison(
                    schedule_nos=cls_result.schedule_nos,
                    tier=cls_result.tier,
                    ifa_concurrence=cls_result.with_ifa,
                    is_pac=cls_result.is_pac,
                )
                resolve_latency = round((time.perf_counter() - t0) * 1000.0, 2)

                if comp_res is not None:
                    all_citations = []
                    for r in comp_res.schedules:
                        all_citations.extend(self.anchorer.anchor_structured_record(r))
                    citations_data = [c.model_dump() for c in all_citations]

                    yield {
                        "event": "message",
                        "data": self._make_event(
                            stage="resolve",
                            data={
                                "query_id": q_id,
                                "answer": comp_res.formatted_answer,
                                "citations": citations_data,
                                "latency_ms": resolve_latency,
                            },
                        ),
                    }

                    total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)
                    yield {
                        "event": "message",
                        "data": self._make_event(
                            stage="complete",
                            data={
                                "query_id": q_id,
                                "answer": comp_res.formatted_answer,
                                "citations": citations_data,
                                "latency_ms": total_latency,
                            },
                        ),
                    }

                    try:
                        self.audit.record_query(
                            query_id=q_id,
                            question=q_clean,
                            answer=comp_res.formatted_answer,
                            citations=citations_data,
                            nli_scores=[],
                            route_type="structured",
                            abstained=False,
                            execution_time_ms=total_latency,
                        )
                    except Exception as a_err:
                        logger.warning(f"[AuditLogger] Failed to record comparative query: {a_err}")
                    return

            # Case A2: Single Schedule Financial Delegation Lookup
            if cls_result.query_type == "structured" and cls_result.schedule_no is not None and cls_result.tier is not None:
                t0 = time.perf_counter()
                res = resolve_dfpds_delegation(
                    schedule_no=cls_result.schedule_no,
                    tier=cls_result.tier,
                    ifa_concurrence=cls_result.with_ifa,
                    is_pac=cls_result.is_pac,
                )
                resolve_latency = round((time.perf_counter() - t0) * 1000.0, 2)

                if res is not None:
                    citations = self.anchorer.anchor_structured_record(res)
                    citations_data = [c.model_dump() for c in citations]

                    yield {
                        "event": "message",
                        "data": self._make_event(
                            stage="resolve",
                            data={
                                "query_id": q_id,
                                "answer": res.formatted_answer,
                                "citations": citations_data,
                                "latency_ms": resolve_latency,
                            },
                        ),
                    }

                    total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)
                    yield {
                        "event": "message",
                        "data": self._make_event(
                            stage="complete",
                            data={
                                "query_id": q_id,
                                "answer": res.formatted_answer,
                                "citations": citations_data,
                                "latency_ms": total_latency,
                            },
                        ),
                    }

                    # Audit Record Commit
                    try:
                        self.audit.record_query(
                            query_id=q_id,
                            question=q_clean,
                            answer=res.formatted_answer,
                            citations=citations_data,
                            nli_scores=[],
                            route_type="structured",
                            abstained=False,
                            execution_time_ms=total_latency,
                        )
                    except Exception as a_err:
                        logger.warning(f"[AuditLogger] Failed to record structured query: {a_err}")
                    return

            # If structured query resolution returned None and is clearly out of range (e.g. Schedule 99)
            if cls_result.query_type == "structured" and (
                cls_result.schedule_no is not None and (cls_result.schedule_no < 1 or cls_result.schedule_no > 32)
            ):
                refusal = self.abstention.create_refusal(
                    query=q_clean,
                    code=RefusalReasonCode.OUT_OF_DOMAIN_QUERY,
                    details=f"Schedule {cls_result.schedule_no} is outside the statutory DFPDS-2026 range (Schedules 01–32).",
                )
                total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)
                yield {
                    "event": "message",
                    "data": self._make_event(
                        stage="abstain",
                        data={
                            "query_id": q_id,
                            "reason": refusal.code.value,
                            "explanation": refusal.explanation,
                            "remedy_suggestions": refusal.remedy_suggestions,
                            "latency_ms": total_latency,
                        },
                    ),
                }

                # Audit Record Commit (Structured Abstention)
                try:
                    self.audit.record_query(
                        query_id=q_id,
                        question=q_clean,
                        answer=refusal.explanation,
                        citations=[],
                        nli_scores=[],
                        route_type="structured",
                        abstained=True,
                        refusal_reason=refusal.code.value,
                        execution_time_ms=total_latency,
                    )
                except Exception as a_err:
                    logger.warning(f"[AuditLogger] Failed to record structured abstention: {a_err}")
                return

            # =========================================================================
            # PATH B: INTERPRETIVE HYBRID RAG + NLI GATE
            # =========================================================================
            # 2. RETRIEVE STAGE
            t0 = time.perf_counter()
            retrieved_chunks = self.hybrid.retrieve(q_clean, top_k=10)
            retrieve_latency = round((time.perf_counter() - t0) * 1000.0, 2)

            yield {
                "event": "message",
                "data": self._make_event(
                    stage="retrieve",
                    data={
                        "query_id": q_id,
                        "chunks": len(retrieved_chunks),
                        "latency_ms": retrieve_latency,
                    },
                ),
            }

            if not retrieved_chunks:
                refusal = self.abstention.create_refusal(
                    query=q_clean,
                    code=RefusalReasonCode.INSUFFICIENT_CORPUS_CONTEXT,
                )
                total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)
                yield {
                    "event": "message",
                    "data": self._make_event(
                        stage="abstain",
                        data={
                            "query_id": q_id,
                            "reason": refusal.code.value,
                            "explanation": refusal.explanation,
                            "remedy_suggestions": refusal.remedy_suggestions,
                            "latency_ms": total_latency,
                        },
                    ),
                }

                # Audit Record Commit (No Chunks Abstention)
                try:
                    self.audit.record_query(
                        query_id=q_id,
                        question=q_clean,
                        answer=refusal.explanation,
                        citations=[],
                        nli_scores=[],
                        route_type="interpretive",
                        abstained=True,
                        refusal_reason=refusal.code.value,
                        execution_time_ms=total_latency,
                    )
                except Exception as a_err:
                    logger.warning(f"[AuditLogger] Failed to record empty retrieval abstention: {a_err}")
                return

            # 3. RERANK STAGE
            t0 = time.perf_counter()
            reranked_chunks = self.reranker.rerank(q_clean, retrieved_chunks, top_k=3)
            rerank_latency = round((time.perf_counter() - t0) * 1000.0, 2)

            top_chunks_data = [
                {
                    "id": c.chunk_id,
                    "document": c.breadcrumb,
                    "score": float(round(c.score, 4)),
                    "text_preview": c.text[:140].strip() if c.text else "",
                }
                for c in reranked_chunks
            ]

            yield {
                "event": "message",
                "data": self._make_event(
                    stage="rerank",
                    data={
                        "query_id": q_id,
                        "top_chunks": top_chunks_data,
                        "latency_ms": rerank_latency,
                    },
                ),
            }

            # 4. CORRECTIVE GATE STAGE
            t0 = time.perf_counter()
            filtered_chunks, is_sufficient = self.gate.filter_chunks(q_clean, reranked_chunks)
            gate_latency = round((time.perf_counter() - t0) * 1000.0, 2)

            yield {
                "event": "message",
                "data": self._make_event(
                    stage="gate",
                    data={
                        "query_id": q_id,
                        "relevant": is_sufficient,
                        "latency_ms": gate_latency,
                    },
                ),
            }

            if not is_sufficient or not filtered_chunks:
                refusal = self.abstention.create_refusal(
                    query=q_clean,
                    code=RefusalReasonCode.INSUFFICIENT_CORPUS_CONTEXT,
                )
                total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)
                yield {
                    "event": "message",
                    "data": self._make_event(
                        stage="abstain",
                        data={
                            "query_id": q_id,
                            "reason": refusal.code.value,
                            "explanation": refusal.explanation,
                            "remedy_suggestions": refusal.remedy_suggestions,
                            "latency_ms": total_latency,
                        },
                    ),
                }

                # Audit Record Commit (Gate Abstention)
                try:
                    self.audit.record_query(
                        query_id=q_id,
                        question=q_clean,
                        answer=refusal.explanation,
                        citations=[],
                        nli_scores=[],
                        route_type="interpretive",
                        abstained=True,
                        refusal_reason=refusal.code.value,
                        execution_time_ms=total_latency,
                    )
                except Exception as a_err:
                    logger.warning(f"[AuditLogger] Failed to record gate abstention: {a_err}")
                return

            # 5. GENERATE STAGE (Streaming Tokens with Disconnect Check)
            if request and await request.is_disconnected():
                logger.info(f"[QueryPipeline] Client disconnected before generation on query '{q_id}'")
                try:
                    self.audit.record_query(
                        query_id=q_id,
                        question=q_clean,
                        answer="Client disconnected before synthesis",
                        citations=[],
                        nli_scores=[],
                        route_type="interpretive",
                        abstained=True,
                        refusal_reason="client_disconnected",
                        execution_time_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                    )
                except Exception:
                    pass
                return

            collected_tokens: list[str] = []
            try:
                for token in self.synthesizer.synthesize_stream(q_clean, filtered_chunks):
                    if request and await request.is_disconnected():
                        logger.info(f"[QueryPipeline] Client disconnected during generation on query '{q_id}'")
                        return
                    collected_tokens.append(token)
                    yield {
                        "event": "message",
                        "data": self._make_event(
                            stage="generate",
                            data={"query_id": q_id, "token": token},
                        ),
                    }
            except Exception as e:
                logger.warning(f"[QueryPipeline] Streaming synthesis failed: {e}")
                fallback_token = filtered_chunks[0].text[:300].strip() if filtered_chunks else ""
                if fallback_token:
                    collected_tokens.append(fallback_token)
                    yield {
                        "event": "message",
                        "data": self._make_event(
                            stage="generate",
                            data={"query_id": q_id, "token": fallback_token},
                        ),
                    }

            full_text = "".join(collected_tokens).strip()

            # Check client disconnect before NLI verification
            if request and await request.is_disconnected():
                logger.info(f"[QueryPipeline] Client disconnected before NLI verification on query '{q_id}'")
                return

            # 6. VERIFY STAGE (Per-Sentence DeBERTa NLI Gate with Archetype Thresholds)
            t0 = time.perf_counter()
            verifications, is_grounded, final_text = self.nli_gate.verify_synthesis(
                text=full_text,
                chunks=filtered_chunks,
                synthesizer=self.synthesizer,
                archetype=cls_result.archetype,
            )
            verify_latency = round((time.perf_counter() - t0) * 1000.0, 2)

            avg_score = 0.0
            if verifications:
                avg_score = float(round(sum(v.entailment_score for v in verifications) / len(verifications), 4))

            yield {
                "event": "message",
                "data": self._make_event(
                    stage="verify",
                    data={
                        "query_id": q_id,
                        "status": "certified" if is_grounded else "abstain",
                        "nli_score": avg_score,
                        "latency_ms": verify_latency,
                    },
                ),
            }

            total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)

            nli_records_data = [
                {
                    "sentence": getattr(v, "text", getattr(v, "sentence", str(v))),
                    "entailment_score": float(round(getattr(v, "entailment_score", 0.0), 4)),
                    "contradiction_score": float(round(getattr(v, "contradiction_score", 0.0), 4)),
                    "status": getattr(v, "status", "certified"),
                }
                for v in verifications
            ] if verifications else []

            if is_grounded:
                citations = self.anchorer.anchor_verified_sentences(verifications, filtered_chunks)
                citations_data = [c.model_dump() for c in citations]

                yield {
                    "event": "message",
                    "data": self._make_event(
                        stage="complete",
                        data={
                            "query_id": q_id,
                            "answer": final_text or full_text,
                            "citations": citations_data,
                            "latency_ms": total_latency,
                        },
                    ),
                }

                # Audit Record Commit (Verified Grounded Synthesis)
                try:
                    self.audit.record_query(
                        query_id=q_id,
                        question=q_clean,
                        answer=final_text or full_text,
                        citations=citations_data,
                        nli_scores=nli_records_data,
                        route_type="interpretive",
                        abstained=False,
                        execution_time_ms=total_latency,
                    )
                except Exception as a_err:
                    logger.warning(f"[AuditLogger] Failed to record grounded query: {a_err}")
            else:
                refusal = self.abstention.create_refusal(
                    query=q_clean,
                    code=RefusalReasonCode.UNVERIFIED_STATUTORY_CLAIM,
                    nli_records=verifications,
                )
                yield {
                    "event": "message",
                    "data": self._make_event(
                        stage="abstain",
                        data={
                            "query_id": q_id,
                            "reason": refusal.code.value,
                            "explanation": refusal.explanation,
                            "remedy_suggestions": refusal.remedy_suggestions,
                            "latency_ms": total_latency,
                        },
                    ),
                }

                # Audit Record Commit (NLI Refusal)
                try:
                    self.audit.record_query(
                        query_id=q_id,
                        question=q_clean,
                        answer=refusal.explanation,
                        citations=[],
                        nli_scores=nli_records_data,
                        route_type="interpretive",
                        abstained=True,
                        refusal_reason=refusal.code.value,
                        execution_time_ms=total_latency,
                    )
                except Exception as a_err:
                    logger.warning(f"[AuditLogger] Failed to record NLI refusal: {a_err}")

        except asyncio.CancelledError:
            logger.info(f"[QueryPipeline] Streaming connection cancelled for query '{q_id}'")
            try:
                self.audit.record_query(
                    query_id=q_id,
                    question=q_clean,
                    answer="Connection cancelled by client",
                    citations=[],
                    nli_scores=[],
                    route_type="interpretive",
                    abstained=True,
                    refusal_reason="client_disconnected",
                    execution_time_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                )
            except Exception:
                pass
            raise

        except Exception as exc:
            logger.error(f"[QueryPipeline] Execution failure on query '{question}': {exc}", exc_info=True)
            yield {
                "event": "message",
                "data": self._make_event(
                    stage="error",
                    data={"query_id": q_id, "error": "Internal pipeline error during regulatory processing."},
                ),
            }


orchestrator = QueryPipelineOrchestrator()


@router.post("/query", status_code=status.HTTP_200_OK)
async def query_endpoint(req: QueryRequest, request: Request) -> Any:
    """
    Unified Query Endpoint supporting both SSE Streaming and direct JSON responses.
    """
    if req.stream:
        return EventSourceResponse(
            orchestrator.execute_stream(req.question, query_id=req.query_id, request=request),
            media_type="text/event-stream",
        )

    # Non-streaming response aggregation
    events: list[dict[str, Any]] = []
    final_answer: Optional[str] = None
    citations: list[dict[str, Any]] = []
    refusal_reason: Optional[str] = None
    refusal_explanation: Optional[str] = None
    query_type = "interpretive"
    status_str = "complete"
    final_query_id = req.query_id or f"q_{uuid.uuid4().hex[:12]}"

    async for event_dict in orchestrator.execute_stream(req.question, query_id=req.query_id):
        data_str = event_dict.get("data", "{}")
        parsed = json.loads(data_str)
        stage = parsed.get("stage")
        data = parsed.get("data", {})
        events.append(parsed)

        if "query_id" in data and data["query_id"]:
            final_query_id = data["query_id"]

        if stage == "classify":
            query_type = data.get("type", "interpretive")
        elif stage in ("resolve", "complete"):
            final_answer = data.get("answer")
            citations = data.get("citations", [])
            status_str = "certified"
        elif stage == "abstain":
            refusal_reason = data.get("reason")
            refusal_explanation = data.get("explanation")
            status_str = "abstain"

    return {
        "success": True,
        "data": {
            "query_id": final_query_id,
            "type": query_type,
            "status": status_str,
            "answer": final_answer,
            "citations": citations,
            "reason": refusal_reason,
            "explanation": refusal_explanation,
            "events_count": len(events),
        },
    }
