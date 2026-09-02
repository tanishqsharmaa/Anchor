"""
synthesizer.py — Constrained LLM Natural Language Synthesis Engine
"""

import logging
from typing import Iterator, Optional
from anchor.models.generator import QwenGenerator
from anchor.retrieve.hybrid import RetrievedChunk

logger = logging.getLogger(__name__)


class Synthesizer:
    """
    Constrained Natural Language Synthesizer for PROJECT ANCHOR.
    Constructs strict military grounding prompts from retrieved regulatory context chunks
    and orchestrates synchronous or streaming generation via local Qwen2.5-7B.
    """

    def __init__(self, generator: Optional[QwenGenerator] = None) -> None:
        self._generator = generator

    @property
    def generator(self) -> QwenGenerator:
        """Lazy load QwenGenerator on demand."""
        if self._generator is None:
            self._generator = QwenGenerator()
        return self._generator

    def build_grounding_system_prompt(self) -> str:
        """
        Construct strict compliance system prompt constraining output strictly to context.
        """
        return (
            "You are an AI Compliance Officer for the Indian Navy operating within PROJECT ANCHOR.\n"
            "Your mission is to provide strictly factual, precise answers to naval procurement and regulatory questions.\n\n"
            "MANDATORY COMPLIANCE RULES:\n"
            "1. Base your answer EXCLUSIVELY on the factual statements directly contained in the provided context chunks.\n"
            "2. Do NOT extrapolate, speculate, or introduce assumptions not explicitly substantiated by the text.\n"
            "3. State precise financial limits, Competent Financial Authority (CFA) appointments, Schedule numbers, and Integrated Financial Advisor (IFA) concurrence rules exactly as they appear in the context.\n"
            "4. If the provided context is insufficient to answer the query or if there is conflicting information, state clearly what facts are verified."
        )

    def format_context(self, chunks: list[RetrievedChunk]) -> str:
        """
        Format context chunks into structured, attributed sections for prompt ingestion.
        """
        if not chunks:
            return ""

        context_blocks: list[str] = ["[CONTEXT CHUNKS]"]
        for idx, chunk in enumerate(chunks, 1):
            block = (
                f"[Chunk {idx}] Source: {chunk.doc_id} | Breadcrumb: {chunk.breadcrumb} | Page: {chunk.page_no}\n"
                f"{chunk.text.strip()}"
            )
            context_blocks.append(block)

        return "\n\n".join(context_blocks)

    def build_user_prompt(self, query: str, chunks: list[RetrievedChunk]) -> str:
        """
        Build complete user prompt with formatted context and query.
        """
        context_str = self.format_context(chunks)
        return (
            f"{context_str}\n\n"
            f"[QUERY]\n{query.strip()}\n\n"
            f"[INSTRUCTION]\n"
            f"Synthesize a concise, direct, and verifiable answer based ONLY on the context chunks above."
        )

    def synthesize(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        temperature: float = 0.1,
        max_tokens: Optional[int] = 512,
    ) -> str:
        """
        Synthesize natural language answer synchronously.

        Args:
            query: User question string.
            chunks: Filtered top-k context chunks from retriever/reranker.
            temperature: Sampling temperature (default 0.1).
            max_tokens: Maximum response tokens.

        Returns:
            str: Grounded answer text.
        """
        if not chunks:
            return "No relevant regulatory context provided to answer the query."

        user_prompt = self.build_user_prompt(query, chunks)
        system_prompt = self.build_grounding_system_prompt()

        return self.generator.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def synthesize_stream(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        temperature: float = 0.1,
        max_tokens: Optional[int] = 512,
    ) -> Iterator[str]:
        """
        Synthesize natural language answer as a stream of tokens for SSE transmission.

        Args:
            query: User question string.
            chunks: Filtered top-k context chunks from retriever/reranker.
            temperature: Sampling temperature (default 0.1).
            max_tokens: Maximum response tokens.

        Yields:
            str: Generated tokens in real time.
        """
        if not chunks:
            yield "No relevant regulatory context provided to answer the query."
            return

        user_prompt = self.build_user_prompt(query, chunks)
        system_prompt = self.build_grounding_system_prompt()

        yield from self.generator.generate_stream(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
