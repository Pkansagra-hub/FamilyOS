"""
CA1 Semantic Bridge Module

This module implements the CA1 region of the hippocampus, responsible for:
- Extracting semantic meaning from encoded events
- Generating semantic triples for knowledge graph storage
- Creating temporal hints for time-based organization
- Projecting hippocampal memories to semantic stores

The CA1 bridge takes hippocampal encodings and extracts structured semantic
information including time expressions, entity mentions, and topic keywords.

Semantic Extraction Pipeline:
1. Time Extraction - Parse temporal expressions to ISO timestamps
2. Mention Extraction - Identify person/entity references
3. Topic Extraction - Extract salient keywords and categories
4. Triple Generation - Convert to (subject, predicate, object) facts
5. Storage Projection - Send to SemanticStore via UnitOfWork

Storage Integration:
- Uses dependency injection for testability
- Coordinates with semantic_store via UnitOfWork
- Provides temporal hints for bucket organization
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

from hippocampus.types import HippocampalEncoding, SemanticProjection
from observability.logging import get_json_logger

logger = get_json_logger(__name__)


class SemanticStoreProtocol(Protocol):
    """Protocol for semantic storage operations."""

    async def store_triples(
        self, facts: List[Tuple[str, str, str]], metadata: Dict[str, Any]
    ) -> None:
        """Store semantic triples with metadata."""
        ...


@dataclass
class ExtractionConfig:
    """Configuration for CA1 semantic extraction."""

    extract_time: bool = True  # Extract temporal expressions
    extract_mentions: bool = True  # Extract person/entity mentions
    extract_topics: bool = True  # Extract topic keywords
    min_confidence: float = 0.5  # Minimum confidence for facts
    max_topics: int = 5  # Maximum topics to extract


class CA1SemanticBridge:
    """
    CA1 Semantic Bridge implementation.

    Extracts semantic meaning from hippocampal encodings and projects
    structured facts to knowledge graph storage.
    """

    def __init__(
        self,
        config: Optional[ExtractionConfig] = None,
        semantic_store: Optional[SemanticStoreProtocol] = None,
    ):
        self.config = config or ExtractionConfig()
        self.semantic_store = semantic_store

        # Simple patterns for demonstration (production would use NLP models)
        self.time_patterns = [
            (r"\b(\d{1,2}:\d{2})\s*(am|pm)?\b", "time_of_day"),
            (r"\b(today|tomorrow|yesterday)\b", "relative_day"),
            (
                r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                "day_of_week",
            ),
            (r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", "date_mdy"),
            (
                r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
                "month_name",
            ),
        ]

        self.mention_patterns = [
            (r"\b([A-Z][a-z]+)\s+(?:said|told|called|invited|met)\b", "person_action"),
            (r"\bwith\s+([A-Z][a-z]+)\b", "person_with"),
            (r"\b([A-Z][a-z]+)\'s\s+\w+\b", "person_possessive"),
            (r"\b@([A-Za-z0-9_]+)\b", "username"),
        ]

        self.topic_keywords = {
            "birthday": [
                "birthday",
                "party",
                "celebration",
                "cake",
                "gifts",
                "candles",
            ],
            "work": [
                "meeting",
                "project",
                "deadline",
                "office",
                "colleague",
                "presentation",
            ],
            "family": ["family", "mom", "dad", "brother", "sister", "parents", "kids"],
            "travel": ["trip", "vacation", "flight", "hotel", "destination", "journey"],
            "food": ["restaurant", "dinner", "lunch", "breakfast", "cooking", "recipe"],
        }

        logger.info(
            "CA1SemanticBridge initialized",
            extra={
                "extract_time": self.config.extract_time,
                "extract_mentions": self.config.extract_mentions,
                "extract_topics": self.config.extract_topics,
                "has_semantic_store": self.semantic_store is not None,
            },
        )

    async def extract_semantics(
        self, encoding: HippocampalEncoding, text: str
    ) -> SemanticProjection:
        """
        Extract semantic meaning from hippocampal encoding.

        Args:
            encoding: Hippocampal encoding with codes and metadata
            text: Original text that was encoded

        Returns:
            SemanticProjection with facts, temporal hints, and confidence
        """
        logger.info(
            "Starting semantic extraction",
            extra={
                "event_id": encoding.event_id,
                "space_id": encoding.space_id,
                "text_length": len(text),
                "novelty": encoding.novelty,
            },
        )

        facts = []
        temporal_hints = {}
        confidence_scores = []

        # Extract temporal facts
        if self.config.extract_time:
            time_facts, time_hints = await self._extract_temporal(
                encoding.event_id, text
            )
            facts.extend(time_facts)
            temporal_hints.update(time_hints)
            confidence_scores.extend(
                [0.8] * len(time_facts)
            )  # High confidence for time patterns

        # Extract mention facts
        if self.config.extract_mentions:
            mention_facts = await self._extract_mentions(encoding.event_id, text)
            facts.extend(mention_facts)
            confidence_scores.extend(
                [0.7] * len(mention_facts)
            )  # Medium confidence for mentions

        # Extract topic facts
        if self.config.extract_topics:
            topic_facts = await self._extract_topics(encoding.event_id, text)
            facts.extend(topic_facts)
            confidence_scores.extend(
                [0.6] * len(topic_facts)
            )  # Lower confidence for topics

        # Calculate overall confidence
        overall_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0
        )

        # Filter facts by confidence
        filtered_facts = [
            fact
            for i, fact in enumerate(facts)
            if i < len(confidence_scores)
            and confidence_scores[i] >= self.config.min_confidence
        ]

        projection = SemanticProjection(
            facts=filtered_facts,
            temporal_hints=temporal_hints,
            confidence=overall_confidence,
            metadata={
                "source_event": encoding.event_id,
                "space_id": encoding.space_id,
                "novelty": encoding.novelty,
                "extraction_config": {
                    "time": self.config.extract_time,
                    "mentions": self.config.extract_mentions,
                    "topics": self.config.extract_topics,
                },
            },
        )

        logger.info(
            "Semantic extraction complete",
            extra={
                "event_id": encoding.event_id,
                "total_facts": len(facts),
                "filtered_facts": len(filtered_facts),
                "confidence": overall_confidence,
                "temporal_hints": len(temporal_hints),
            },
        )

        return projection

    async def _extract_temporal(
        self, event_id: str, text: str
    ) -> Tuple[List[Tuple[str, str, str]], Dict[str, str]]:
        """Extract temporal facts and hints from text."""
        facts = []
        hints = {}

        text_lower = text.lower()

        for pattern, time_type in self.time_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if time_type == "time_of_day":
                    time_value = match.group(0)
                    facts.append((f"event:{event_id}", "has_time", time_value))
                    # Generate bucket hint for time-based organization
                    hour = int(match.group(1).split(":")[0])
                    if hour < 12:
                        hints["time_bucket"] = "morning"
                    elif hour < 17:
                        hints["time_bucket"] = "afternoon"
                    else:
                        hints["time_bucket"] = "evening"

                elif time_type == "relative_day":
                    day_value = match.group(0)
                    facts.append((f"event:{event_id}", "occurs_on", day_value))
                    hints["day_bucket"] = day_value

                elif time_type == "day_of_week":
                    day_value = match.group(0)
                    facts.append((f"event:{event_id}", "day_of_week", day_value))
                    hints["weekday_bucket"] = day_value

                elif time_type == "date_mdy":
                    month, day, year = match.groups()
                    date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    facts.append((f"event:{event_id}", "has_date", date_str))
                    hints["date_bucket"] = f"{year}-{month.zfill(2)}"

        return facts, hints

    async def _extract_mentions(
        self, event_id: str, text: str
    ) -> List[Tuple[str, str, str]]:
        """Extract person/entity mentions from text."""
        facts = []

        for pattern, mention_type in self.mention_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if mention_type in [
                    "person_action",
                    "person_with",
                    "person_possessive",
                ]:
                    person_name = match.group(1).lower()
                    facts.append(
                        (f"event:{event_id}", "mentions", f"person:{person_name}")
                    )
                elif mention_type == "username":
                    username = match.group(1).lower()
                    facts.append((f"event:{event_id}", "mentions", f"user:{username}"))

        return facts

    async def _extract_topics(
        self, event_id: str, text: str
    ) -> List[Tuple[str, str, str]]:
        """Extract topic keywords from text."""
        facts = []
        text_lower = text.lower()

        topic_scores = {}

        # Score topics based on keyword matches
        for topic, keywords in self.topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                topic_scores[topic] = score

        # Take top topics up to max_topics limit
        top_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[
            : self.config.max_topics
        ]

        for topic, score in top_topics:
            facts.append((f"event:{event_id}", "has_topic", topic))
            # Also add a confidence fact
            facts.append((f"event:{event_id}", "topic_confidence", f"{topic}:{score}"))

        return facts

    async def project_to_storage(self, projection: SemanticProjection) -> bool:
        """Project semantic facts to storage layer."""
        if not self.semantic_store:
            logger.warning("No semantic store available for projection")
            return False

        try:
            await self.semantic_store.store_triples(
                projection.facts,
                {
                    "temporal_hints": projection.temporal_hints,
                    "confidence": projection.confidence,
                    "metadata": projection.metadata,
                },
            )

            logger.info(
                "Semantic projection stored",
                extra={
                    "fact_count": len(projection.facts),
                    "confidence": projection.confidence,
                    "temporal_hints": len(projection.temporal_hints),
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to project semantics to storage", extra={"error": str(e)}
            )
            return False


# TODO: Production enhancements
# - Replace regex patterns with proper NLP models (spaCy, NLTK)
# - Add entity linking and coreference resolution
# - Implement more sophisticated temporal parsing
# - Add confidence calibration based on training data
# - Add caching for frequently extracted patterns
