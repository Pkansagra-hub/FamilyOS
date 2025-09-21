"""
CA3 Pattern Completion Module

This module implements the CA3 region of the hippocampus, responsible for:
- Content-addressable memory recall based on partial cues
- Pattern completion using stored memory codes
- Score fusion combining vector similarity and SDR Hamming distance
- Ranked candidate retrieval with explanations

The CA3 completer takes partial cues and finds the most similar stored memories
using a hybrid scoring approach that combines semantic (vector) and structural (SDR) similarity.

Math Foundation:
- Score Fusion: score = λ·cos(q,v) + (1-λ)·(1-d_H/B)
- Where λ=0.7 when vectors available, λ=0.0 for pure SDR mode
- d_H = Hamming distance, B = 512 (bits), cos = cosine similarity

Storage Integration:
- Uses dependency injection for testability
- Coordinates with hippocampus_store, vector_store via UnitOfWork
- Graceful degradation when stores not available
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from hippocampus.sdr import SDRProcessor
from hippocampus.types import CompletionCandidate, SDRCodes
from observability.logging import get_json_logger

logger = get_json_logger(__name__)


class HippocampusStoreProtocol(Protocol):
    """Protocol for hippocampus storage operations."""

    def find_codes_in_space(
        self, space_id: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Find all stored codes within a space."""
        ...


class VectorStoreProtocol(Protocol):
    """Protocol for vector storage operations."""

    def get_embedding(self, event_id: str) -> Optional[List[float]]:
        """Get embedding vector for an event."""
        ...

    def cosine_similarity(self, vector_a: List[float], vector_b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        ...


@dataclass
class CompletionConfig:
    """Configuration for CA3 pattern completion."""

    lambda_weight: float = (
        0.7  # Weight for vector vs SDR scoring (0.7 when vectors available)
    )
    max_candidates: int = 1000  # Maximum candidates to consider
    hamming_bits: int = 512  # SDR bit width for Hamming normalization
    min_score: float = 0.1  # Minimum score threshold for results


class CA3PatternCompleter:
    """
    CA3 Pattern Completion implementation.

    Implements content-addressable memory recall using hybrid scoring
    that combines vector cosine similarity with SDR Hamming distance.
    """

    def __init__(
        self,
        sdr_processor: SDRProcessor,
        config: Optional[CompletionConfig] = None,
        hippocampus_store: Optional[HippocampusStoreProtocol] = None,
        vector_store: Optional[VectorStoreProtocol] = None,
    ):
        self.sdr_processor = sdr_processor
        self.config = config or CompletionConfig()
        self.hippocampus_store = hippocampus_store
        self.vector_store = vector_store

        logger.info(
            "CA3PatternCompleter initialized",
            extra={
                "lambda_weight": self.config.lambda_weight,
                "max_candidates": self.config.max_candidates,
                "has_hippocampus_store": self.hippocampus_store is not None,
                "has_vector_store": self.vector_store is not None,
            },
        )

    def complete_pattern(
        self,
        space_id: str,
        cue_text: str,
        k: int = 10,
        cue_embedding: Optional[List[float]] = None,
    ) -> List[CompletionCandidate]:
        """
        Complete a pattern based on a partial cue.

        Args:
            space_id: Space to search within
            cue_text: Text cue for pattern completion
            k: Number of top results to return
            cue_embedding: Optional pre-computed embedding for cue

        Returns:
            List of completion candidates sorted by relevance score

        Raises:
            ValueError: If no storage backends available
        """
        if not self.hippocampus_store:
            raise ValueError("CA3 completion requires hippocampus_store")

        logger.info(
            "Starting CA3 pattern completion",
            extra={
                "space_id": space_id,
                "cue_text": cue_text[:100],  # Truncate for logging
                "k": k,
                "has_cue_embedding": cue_embedding is not None,
            },
        )

        # Step 1: Generate cue codes
        cue_codes = self._generate_cue_codes(cue_text)

        # Step 2: Find candidate memories in space
        candidates = self._find_candidates(space_id)

        if not candidates:
            logger.warning("No candidates found in space", extra={"space_id": space_id})
            return []

        # Step 3: Score and rank candidates
        scored_candidates = self._score_candidates(cue_codes, cue_embedding, candidates)

        # Step 4: Filter and return top-k
        filtered_candidates = [
            candidate
            for candidate in scored_candidates
            if candidate.score >= self.config.min_score
        ]

        result = filtered_candidates[:k]

        logger.info(
            "CA3 pattern completion complete",
            extra={
                "space_id": space_id,
                "total_candidates": len(candidates),
                "scored_candidates": len(scored_candidates),
                "filtered_candidates": len(filtered_candidates),
                "returned_results": len(result),
                "top_score": result[0].score if result else 0.0,
            },
        )

        return result

    def _generate_cue_codes(self, cue_text: str) -> SDRCodes:
        """Generate SDR codes for the cue text."""
        try:
            # Use same tokenization and coding as DG
            tokens = self.sdr_processor.tokenize_to_shingles(cue_text)
            simhash_bits, simhash_hex = self.sdr_processor.compute_simhash(tokens)
            minhash = self.sdr_processor.compute_minhash(tokens)

            codes = SDRCodes(
                simhash_bits=simhash_bits,
                simhash_hex=simhash_hex,
                minhash32=minhash,
                tokens=tokens,
                text_length=len(cue_text),
            )

            logger.debug(
                "Generated cue codes",
                extra={
                    "token_count": len(tokens),
                    "simhash": simhash_hex[:16] + "...",  # Truncate for logging
                    "minhash_sample": minhash[:3],
                },
            )

            return codes

        except Exception as e:
            logger.error("Failed to generate cue codes", extra={"error": str(e)})
            raise

    def _find_candidates(self, space_id: str) -> List[Dict[str, Any]]:
        """Find candidate memories in the specified space."""
        try:
            if not self.hippocampus_store:
                raise ValueError("HippocampusStore not available")

            candidates = self.hippocampus_store.find_codes_in_space(
                space_id, limit=self.config.max_candidates
            )

            logger.debug(
                "Found candidates",
                extra={"space_id": space_id, "candidate_count": len(candidates)},
            )

            return candidates

        except Exception as e:
            logger.error(
                "Failed to find candidates",
                extra={"space_id": space_id, "error": str(e)},
            )
            raise

    def _score_candidates(
        self,
        cue_codes: SDRCodes,
        cue_embedding: Optional[List[float]],
        candidates: List[Dict[str, Any]],
    ) -> List[CompletionCandidate]:
        """Score candidates using hybrid vector + SDR approach."""
        scored_candidates = []

        # Determine if we're using vector mode
        use_vectors = cue_embedding is not None and self.vector_store is not None

        lambda_weight = self.config.lambda_weight if use_vectors else 0.0

        logger.debug(
            "Scoring candidates",
            extra={
                "candidate_count": len(candidates),
                "use_vectors": use_vectors,
                "lambda_weight": lambda_weight,
            },
        )

        for candidate in candidates:
            try:
                score, explanation = self._score_single_candidate(
                    cue_codes, cue_embedding, candidate, lambda_weight, use_vectors
                )

                completion_candidate = CompletionCandidate(
                    event_id=candidate["event_id"],
                    score=score,
                    explanation=[explanation],  # Convert string to list
                )

                scored_candidates.append(completion_candidate)

            except Exception as e:
                logger.warning(
                    "Failed to score candidate",
                    extra={
                        "event_id": candidate.get("event_id", "unknown"),
                        "error": str(e),
                    },
                )
                continue

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x.score, reverse=True)

        return scored_candidates

    def _score_single_candidate(
        self,
        cue_codes: SDRCodes,
        cue_embedding: Optional[List[float]],
        candidate: Dict[str, Any],
        lambda_weight: float,
        use_vectors: bool,
    ) -> tuple[float, str]:
        """Score a single candidate using hybrid approach."""

        # Parse candidate codes (assume stored format matches expected fields)
        candidate_codes = SDRCodes(
            simhash_bits=candidate.get("simhash_bits", 0),
            simhash_hex=candidate.get("simhash_hex", candidate.get("simhash", "")),
            minhash32=candidate.get("minhash32", candidate.get("minhash", [])),
            tokens=candidate.get("tokens", []),
            text_length=candidate.get("text_length", 0),
        )

        # Calculate SDR component
        hamming_distance = cue_codes.hamming_distance(candidate_codes)
        sdr_similarity = 1.0 - (hamming_distance / self.config.hamming_bits)

        vector_similarity = 0.0
        if use_vectors and cue_embedding:
            try:
                if not self.vector_store:
                    raise ValueError("VectorStore not available")

                candidate_embedding = self.vector_store.get_embedding(
                    candidate["event_id"]
                )
                if candidate_embedding:
                    vector_similarity = self.vector_store.cosine_similarity(
                        cue_embedding, candidate_embedding
                    )
            except Exception as e:
                logger.debug(
                    "Vector similarity calculation failed",
                    extra={"event_id": candidate["event_id"], "error": str(e)},
                )

        # Fusion scoring: score = λ·cos(q,v) + (1-λ)·(1-d_H/B)
        score = (
            lambda_weight * vector_similarity + (1.0 - lambda_weight) * sdr_similarity
        )

        # Build explanation
        if use_vectors:
            explanation = f"vector:cos={vector_similarity:.3f},sdr:hamm={sdr_similarity:.3f},fusion:λ={lambda_weight}"
        else:
            explanation = f"sdr:hamm={sdr_similarity:.3f},pure_sdr_mode"

        return score, explanation


# TODO: Production integration points
# - Wire HippocampusStore.find_codes_in_space() method
# - Wire VectorStore.get_embedding() and cosine_similarity() methods
# - Add embedding service integration for cue_embedding generation
# - Add performance monitoring and SLO validation
# - Add cache layer for frequently accessed candidates
