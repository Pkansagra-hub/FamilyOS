"""
Sparse Distributed Representation (SDR) Algorithms - Production Implementation
===========================================================================

Implements biological-inspired memory coding algorithms:
- Tokenization with k-gram shingles (k=3)
- SimHash: 512-bit binary SDR with weighted token hashing
- MinHash: 64-permutation Jaccard similarity estimation
- Distance calculations for pattern matching

Based on hippocampus README.md specification with full mathematical implementation.
"""

import hashlib
import re
from typing import List, Tuple

from .types import KGRAM_SIZE, MINHASH_PERMS, SIMHASH_BITS, SDRCodes


class SDRProcessor:
    """
    Production SDR processor implementing biological hippocampal algorithms.

    Processes text into sparse distributed representations for pattern
    separation (DG) and pattern completion (CA3) operations.
    """

    def __init__(
        self,
        simhash_bits: int = SIMHASH_BITS,
        minhash_perms: int = MINHASH_PERMS,
        kgram_size: int = KGRAM_SIZE,
    ):
        """Initialize SDR processor with configurable parameters."""
        self.simhash_bits = simhash_bits
        self.minhash_perms = minhash_perms
        self.kgram_size = kgram_size

        # Pre-compute MinHash permutation seeds for consistency
        self.minhash_seeds = [
            int(hashlib.sha256(f"minhash_perm_{i}".encode()).hexdigest()[:8], 16)
            for i in range(minhash_perms)
        ]

    def tokenize_to_shingles(self, text: str) -> List[str]:
        """
        Convert text to k-gram shingles following specification.

        Process:
        1. Lowercase and strip punctuation
        2. Keep only unicode letters and digits
        3. Generate k-gram shingles for robustness to edits

        Args:
            text: Input text string

        Returns:
            List of k-gram shingle strings
        """
        # Normalize: lowercase, keep unicode letters/digits/spaces
        normalized = re.sub(r"[^\w\s]", " ", text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if len(normalized) < self.kgram_size:
            return [normalized] if normalized else []

        # Generate k-gram shingles
        shingles: List[str] = []
        for i in range(len(normalized) - self.kgram_size + 1):
            shingle = normalized[i : i + self.kgram_size]
            shingles.append(shingle)

        return shingles

    def compute_simhash(self, tokens: List[str]) -> Tuple[int, str]:
        """
        Compute 512-bit SimHash following biological specification.

        Algorithm:
        1. For each token t with weight w_t:
        2. For each bit position b ∈ [0,B), accumulate s_b += ±w_t using hash(t)
        3. Set bit b=1 if s_b ≥ 0 else 0

        Args:
            tokens: List of token strings

        Returns:
            Tuple of (binary_integer, hex_string)
        """
        if not tokens:
            return 0, "0" * (self.simhash_bits // 4)

        # Initialize accumulator for each bit position
        accumulator: List[float] = [0.0] * self.simhash_bits

        for token in tokens:
            # Weight is token frequency (can be enhanced)
            weight = 1.0

            # Generate hash and extract bit influences
            token_hash = hashlib.sha256(token.encode()).digest()

            for bit_pos in range(self.simhash_bits):
                # Use hash bytes to determine bit influence
                byte_idx = (bit_pos // 8) % len(token_hash)
                bit_in_byte = bit_pos % 8

                # Extract bit from hash
                bit_value = (token_hash[byte_idx] >> bit_in_byte) & 1

                # Accumulate ±weight based on bit value
                if bit_value:
                    accumulator[bit_pos] += weight
                else:
                    accumulator[bit_pos] -= weight

        # Convert accumulator to binary code
        binary_code = 0
        for bit_pos in range(self.simhash_bits):
            if accumulator[bit_pos] >= 0:
                binary_code |= 1 << bit_pos

        # Convert to hex string
        hex_digits = self.simhash_bits // 4
        hex_string = f"{binary_code:0{hex_digits}x}"

        return binary_code, hex_string

    def compute_minhash(self, tokens: List[str]) -> List[int]:
        """
        Compute MinHash sketch for Jaccard similarity estimation.

        Algorithm:
        1. For shingles set S and permutations h_i
        2. Record min h_i(S) for each permutation
        3. Store as 32-bit values for speed

        Args:
            tokens: List of token strings

        Returns:
            List of 64 x 32-bit MinHash values
        """
        if not tokens:
            return [0] * self.minhash_perms

        # Convert tokens to set for deduplication
        token_set = set(tokens)

        minhash_values: List[int] = []

        for perm_idx in range(self.minhash_perms):
            min_hash = float("inf")

            for token in token_set:
                # Hash token with permutation seed
                combined = f"{self.minhash_seeds[perm_idx]}{token}"
                token_hash = int(hashlib.sha256(combined.encode()).hexdigest()[:8], 16)

                min_hash = min(min_hash, token_hash)

            # Store as 32-bit value
            minhash_values.append(int(min_hash) & 0xFFFFFFFF)

        return minhash_values

    def process_text(self, text: str) -> SDRCodes:
        """
        Complete SDR processing pipeline for input text.

        Args:
            text: Input text string

        Returns:
            SDRCodes object with SimHash, MinHash, and metadata
        """
        # Step 1: Tokenize to k-gram shingles
        tokens = self.tokenize_to_shingles(text)

        # Step 2: Compute SimHash binary representation
        simhash_bits, simhash_hex = self.compute_simhash(tokens)

        # Step 3: Compute MinHash Jaccard sketch
        minhash32 = self.compute_minhash(tokens)

        return SDRCodes(
            simhash_bits=simhash_bits,
            simhash_hex=simhash_hex,
            minhash32=minhash32,
            tokens=tokens,
            text_length=len(text),
        )

    @staticmethod
    def hamming_distance(code1: SDRCodes, code2: SDRCodes) -> int:
        """Calculate Hamming distance between two SimHash codes."""
        return bin(code1.simhash_bits ^ code2.simhash_bits).count("1")

    @staticmethod
    def jaccard_similarity(code1: SDRCodes, code2: SDRCodes) -> float:
        """Estimate Jaccard similarity using MinHash sketches."""
        return code1.jaccard_similarity(code2)

    @staticmethod
    def normalized_hamming_distance(
        code1: SDRCodes, code2: SDRCodes, bits: int = SIMHASH_BITS
    ) -> float:
        """Calculate normalized Hamming distance (0-1 range)."""
        hamming_dist = SDRProcessor.hamming_distance(code1, code2)
        return hamming_dist / bits


# Global SDR processor instance for convenience
sdr_processor = SDRProcessor()


# Convenience functions for direct use
def process_text(text: str) -> SDRCodes:
    """Process text into SDR codes using global processor."""
    return sdr_processor.process_text(text)


def hamming_distance(code1: SDRCodes, code2: SDRCodes) -> int:
    """Calculate Hamming distance between codes."""
    return SDRProcessor.hamming_distance(code1, code2)


def jaccard_similarity(code1: SDRCodes, code2: SDRCodes) -> float:
    """Calculate Jaccard similarity between codes."""
    return SDRProcessor.jaccard_similarity(code1, code2)
