"""
Hippocampus Data Types - Production Implementation
===============================================

Data structures for hippocampal memory coding following biological specification.
All types match the contracts and support the DG/CA3/CA1 pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class HippocampalEncoding:
    """
    Result of DG (Dentate Gyrus) encoding operation.
    Contains sparse distributed representation codes and metadata.
    """

    event_id: str
    space_id: str
    simhash_hex: str  # 512-bit binary code as hex string
    minhash32: List[int]  # 64 x 32-bit values for Jaccard estimation
    novelty: float  # 0-1 novelty score
    near_duplicates: List[Tuple[str, float]]  # [(event_id, hamming_distance), ...]
    length: int  # Original text length
    ts: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompletionCandidate:
    """
    Result of CA3 pattern completion operation.
    Contains candidate event with scoring breakdown.
    """

    event_id: str
    score: float  # Combined score from vector + SDR fusion
    explanation: List[str]  # ["vector:cos=0.92", "sdr:hamm=0.08"]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompletionResult:
    """
    Full result of CA3 completion query.
    Contains ranked candidates and query metadata.
    """

    space_id: str
    cue: str
    candidates: List[CompletionCandidate]
    total_searched: int
    search_time_ms: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SemanticProjection:
    """
    Result of CA1 bridge semantic extraction.
    Contains triples and temporal hints for storage.
    """

    facts: List[Tuple[str, str, str]]  # [(subject, predicate, object), ...]
    temporal_hints: Dict[str, str]  # {"bucket": "2025-09-06-evening"}
    confidence: float  # 0-1 confidence in extraction
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MemoryCue:
    """
    Input cue for memory recall operations.
    Contains query text and optional constraints.
    """

    space_id: str
    cue_text: str
    k: int = 10  # Number of results to return
    filters: Optional[Dict[str, Any]] = None
    include_scores: bool = True


@dataclass
class SDRCodes:
    """
    Sparse distributed representation codes for a piece of text.
    Contains both SimHash binary and MinHash Jaccard representations.
    """

    simhash_bits: int  # 512-bit integer representation
    simhash_hex: str  # Hex string representation
    minhash32: List[int]  # 64 x 32-bit MinHash values
    tokens: List[str]  # Original k-gram tokens
    text_length: int

    def hamming_distance(self, other: "SDRCodes") -> int:
        """Calculate Hamming distance to another SDR code."""
        return bin(self.simhash_bits ^ other.simhash_bits).count("1")

    def jaccard_similarity(self, other: "SDRCodes") -> float:
        """Estimate Jaccard similarity using MinHash."""
        if len(self.minhash32) != len(other.minhash32):
            raise ValueError("MinHash arrays must have same length")

        matches = sum(1 for a, b in zip(self.minhash32, other.minhash32) if a == b)
        return matches / len(self.minhash32)


# Algorithm configuration constants from specification
SIMHASH_BITS = 512  # Binary SDR dimensionality
MINHASH_PERMS = 64  # Number of MinHash permutations
KGRAM_SIZE = 3  # k-gram shingle size
NOVELTY_ALPHA = 6.0  # Novelty calculation scaling factor
NOVELTY_BETA = 1.0  # Duplicate rate penalty
FUSION_LAMBDA_WITH_VECTORS = 0.7  # Vector/SDR fusion weight when embeddings available
FUSION_LAMBDA_NO_VECTORS = 0.0  # Pure SDR when no embeddings
