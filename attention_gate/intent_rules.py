"""
Intent Derivation Rules for Attention Gate

Derives missing or ambiguous intents from request context,
content analysis, and conversation patterns.

Future-ready for learning integration:
- Phase 1: Rule-based pattern matching
- Phase 2: Calibrated confidence scores
- Phase 3: Learning from user corrections
- Phase 4: Neural intent classification
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import DerivedIntent, GateRequest, IntentConfidence, IntentType


class IntentDeriver:
    """
    Rule-based intent derivation with learning hooks.

    Analyzes request content and context to derive likely intents
    when they're missing or ambiguous from fast-path routing.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

        # Pattern matching rules (Phase 1)
        self._init_pattern_rules()

        # Learning integration state (Phase 3)
        self.derivation_history: List[Dict[str, Any]] = []
        self.calibration_enabled = False

    def _init_pattern_rules(self) -> None:
        """Initialize pattern matching rules for intent derivation"""

        # Content patterns for different intent types
        self.content_patterns = {
            IntentType.RECALL: [
                r"\b(remember|recall|what was|find|retrieve|search for)\b",
                r"\b(when did|where did|who was|how did)\b",
                r"\b(last time|previous|before|earlier)\b",
                r"\?(.*)(yesterday|last week|last month)",
            ],
            IntentType.WRITE: [
                r"\b(note|save|record|write down|capture)\b",
                r"\b(important|remember this|don\'t forget)\b",
                r"\b(meeting notes|summary|key points)\b",
                r"^[A-Z][^.!?]*[.!?]$",  # Declarative statements
            ],
            IntentType.PROSPECTIVE_SCHEDULE: [
                r"\b(remind me|schedule|set reminder|don\'t forget)\b",
                r"\b(tomorrow|next week|later|in \d+ days)\b",
                r"\b(appointment|meeting|deadline|due)\b",
                r"\b(at \d+:\d+|on [A-Z][a-z]+day)\b",
            ],
            IntentType.PROJECT: [
                r"\b(plan|project|goal|objective)\b",
                r"\b(track progress|status|milestone)\b",
                r"\b(to-do|task list|action items)\b",
                r"\b(brainstorm|ideas|strategy)\b",
            ],
            IntentType.HIPPO_ENCODE: [
                r"\b(dream|vision|creative|inspiration)\b",
                r"\b(feeling|emotion|mood|state)\b",
                r"\b(reflection|insight|realization)\b",
                r"\b(personal|private|intimate)\b",
            ],
        }

        # Context patterns based on conversation flow
        self.context_patterns = {
            "follow_up_question": r"\b(also|and|what about|speaking of)\b",
            "clarification": r"\b(you mean|clarify|explain|what do you mean)\b",
            "continuation": r"\b(continuing|as I was saying|back to)\b",
            "correction": r"\b(actually|no wait|I meant|correction)\b",
        }

        # Temporal indicators
        self.temporal_patterns = {
            "past": r"\b(yesterday|last|ago|before|earlier|was|did)\b",
            "present": r"\b(now|currently|today|right now|at the moment)\b",
            "future": r"\b(tomorrow|next|later|will|going to|plan to)\b",
        }

    def derive_intents(self, request: GateRequest) -> List[DerivedIntent]:
        """
        Derive likely intents from request content and context.

        Returns ranked list of possible intents with confidence scores.
        """
        content = request.content.text if request.content else ""

        # Quick exit if content is too short
        if len(content.strip()) < 3:
            return []

        derived_intents = []

        # Pattern-based derivation
        pattern_intents = self._derive_from_patterns(content)
        derived_intents.extend(pattern_intents)

        # Context-based derivation
        context_intents = self._derive_from_context(request)
        derived_intents.extend(context_intents)

        # Temporal analysis
        temporal_intents = self._derive_from_temporal(content)
        derived_intents.extend(temporal_intents)

        # Conversation flow analysis
        flow_intents = self._derive_from_conversation_flow(request)
        derived_intents.extend(flow_intents)

        # Deduplicate and rank
        ranked_intents = self._rank_and_deduplicate(derived_intents)

        # Record derivation for learning
        self._record_derivation(request, content, ranked_intents)

        return ranked_intents[:3]  # Return top 3 candidates

    def _derive_from_patterns(self, content: str) -> List[DerivedIntent]:
        """Derive intents using content pattern matching"""
        content_lower = content.lower()
        derived = []

        for intent_type, patterns in self.content_patterns.items():
            matches = 0
            matched_patterns = []

            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    matches += 1
                    matched_patterns.append(pattern)

            if matches > 0:
                # Calculate confidence based on pattern strength
                confidence = min(0.9, 0.3 + (matches * 0.2))

                derived.append(
                    DerivedIntent(
                        intent=intent_type,
                        confidence=IntentConfidence(
                            score=confidence,
                            source="pattern_matching",
                            evidence=f"matched_{matches}_patterns",
                        ),
                        reasoning=f"Content matches {matches} patterns for {intent_type.value}",
                        metadata={
                            "matched_patterns": matched_patterns,
                            "pattern_count": matches,
                        },
                    )
                )

        return derived

    def _derive_from_context(self, request: GateRequest) -> List[DerivedIntent]:
        """Derive intents from request context and metadata"""
        derived = []

        # Check affect signals
        if request.affect:
            if "urgent" in request.affect.tags:
                # Urgent affect suggests prospective scheduling
                derived.append(
                    DerivedIntent(
                        intent=IntentType.PROSPECTIVE_SCHEDULE,
                        confidence=IntentConfidence(
                            score=0.7,
                            source="affect_analysis",
                            evidence="urgent_affect_tag",
                        ),
                        reasoning="Urgent affect suggests time-sensitive planning",
                        metadata={"affect_tags": request.affect.tags},
                    )
                )

            if "reflective" in request.affect.tags:
                # Reflective affect suggests encoding
                derived.append(
                    DerivedIntent(
                        intent=IntentType.HIPPO_ENCODE,
                        confidence=IntentConfidence(
                            score=0.6,
                            source="affect_analysis",
                            evidence="reflective_affect_tag",
                        ),
                        reasoning="Reflective affect suggests memory encoding",
                        metadata={"affect_tags": request.affect.tags},
                    )
                )

        # Check conversation context
        if request.conversation_context:
            context = request.conversation_context

            # Previous turn analysis
            if context.previous_intent == IntentType.RECALL:
                # Follow-up to recall might be more recall or writing
                derived.append(
                    DerivedIntent(
                        intent=IntentType.RECALL,
                        confidence=IntentConfidence(
                            score=0.5,
                            source="conversation_flow",
                            evidence="recall_continuation",
                        ),
                        reasoning="Continuation of recall conversation",
                        metadata={"previous_intent": context.previous_intent.value},
                    )
                )

        return derived

    def _derive_from_temporal(self, content: str) -> List[DerivedIntent]:
        """Derive intents from temporal language patterns"""
        content_lower = content.lower()
        derived = []

        # Check for temporal indicators
        temporal_signals = {}
        for time_type, pattern in self.temporal_patterns.items():
            if re.search(pattern, content_lower):
                temporal_signals[time_type] = True

        # Future references suggest scheduling
        if temporal_signals.get("future", False):
            derived.append(
                DerivedIntent(
                    intent=IntentType.PROSPECTIVE_SCHEDULE,
                    confidence=IntentConfidence(
                        score=0.6,
                        source="temporal_analysis",
                        evidence="future_references",
                    ),
                    reasoning="Future temporal references suggest scheduling intent",
                    metadata={"temporal_signals": temporal_signals},
                )
            )

        # Past references suggest recall
        if temporal_signals.get("past", False):
            derived.append(
                DerivedIntent(
                    intent=IntentType.RECALL,
                    confidence=IntentConfidence(
                        score=0.5,
                        source="temporal_analysis",
                        evidence="past_references",
                    ),
                    reasoning="Past temporal references suggest recall intent",
                    metadata={"temporal_signals": temporal_signals},
                )
            )

        return derived

    def _derive_from_conversation_flow(
        self, request: GateRequest
    ) -> List[DerivedIntent]:
        """Derive intents from conversation flow patterns"""
        content = request.content.text if request.content else ""
        content_lower = content.lower()
        derived = []

        # Check for conversation flow indicators
        flow_signals = {}
        for flow_type, pattern in self.context_patterns.items():
            if re.search(pattern, content_lower):
                flow_signals[flow_type] = True

        # Follow-up questions suggest recall
        if flow_signals.get("follow_up_question", False):
            derived.append(
                DerivedIntent(
                    intent=IntentType.RECALL,
                    confidence=IntentConfidence(
                        score=0.4,
                        source="conversation_flow",
                        evidence="follow_up_pattern",
                    ),
                    reasoning="Follow-up question pattern suggests information retrieval",
                    metadata={"flow_signals": flow_signals},
                )
            )

        # Clarification requests suggest recall
        if flow_signals.get("clarification", False):
            derived.append(
                DerivedIntent(
                    intent=IntentType.RECALL,
                    confidence=IntentConfidence(
                        score=0.5,
                        source="conversation_flow",
                        evidence="clarification_pattern",
                    ),
                    reasoning="Clarification request suggests memory retrieval",
                    metadata={"flow_signals": flow_signals},
                )
            )

        return derived

    def _rank_and_deduplicate(
        self, intents: List[DerivedIntent]
    ) -> List[DerivedIntent]:
        """Rank intents by confidence and deduplicate"""
        if not intents:
            return []

        # Group by intent type
        intent_groups: Dict[IntentType, List[DerivedIntent]] = {}
        for intent in intents:
            if intent.intent not in intent_groups:
                intent_groups[intent.intent] = []
            intent_groups[intent.intent].append(intent)

        # Merge intents of same type with combined confidence
        merged_intents = []
        for intent_type, group in intent_groups.items():
            if len(group) == 1:
                merged_intents.append(group[0])
            else:
                # Combine confidences using weighted average
                total_confidence = sum(intent.confidence.score for intent in group)
                weight_factor = min(1.0, len(group) * 0.2)  # Bonus for multiple sources
                combined_confidence = min(0.95, total_confidence * weight_factor)

                # Combine evidence
                all_sources = [intent.confidence.source for intent in group]
                all_evidence = [intent.confidence.evidence for intent in group]
                combined_reasoning = (
                    f"Multiple indicators: {', '.join(set(all_evidence))}"
                )

                merged_intents.append(
                    DerivedIntent(
                        intent=intent_type,
                        confidence=IntentConfidence(
                            score=combined_confidence,
                            source=f"combined({','.join(set(all_sources))})",
                            evidence=f"multiple_sources_{len(group)}",
                        ),
                        reasoning=combined_reasoning,
                        metadata={
                            "source_count": len(group),
                            "individual_scores": [i.confidence.score for i in group],
                        },
                    )
                )

        # Sort by confidence descending
        return sorted(merged_intents, key=lambda x: x.confidence.score, reverse=True)

    def _record_derivation(
        self, request: GateRequest, content: str, derived_intents: List[DerivedIntent]
    ) -> None:
        """Record derivation for learning integration"""
        if len(self.derivation_history) > 500:
            # Keep only recent derivations
            self.derivation_history = self.derivation_history[-250:]

        self.derivation_history.append(
            {
                "request_id": request.request_id,
                "content_length": len(content),
                "derived_count": len(derived_intents),
                "top_intent": (
                    derived_intents[0].intent.value if derived_intents else None
                ),
                "top_confidence": (
                    derived_intents[0].confidence.score if derived_intents else 0.0
                ),
                "timestamp": datetime.now().isoformat(),
            }
        )

    # Learning Integration Methods (Future Phases)

    def calibrate_confidence(self, user_feedback: Dict[str, Any]) -> None:
        """Calibrate confidence scores based on user feedback (Phase 2)"""
        if not self.calibration_enabled:
            return

        # TODO: Implement confidence calibration
        # This would adjust pattern weights based on user corrections
        pass

    def get_derivation_stats(self) -> Dict[str, Any]:
        """Get derivation performance statistics"""
        if not self.derivation_history:
            return {"status": "no_data"}

        recent_derivations = self.derivation_history[-100:]

        intent_distribution = {}
        confidence_scores = []

        for record in recent_derivations:
            top_intent = record.get("top_intent")
            if top_intent:
                intent_distribution[top_intent] = (
                    intent_distribution.get(top_intent, 0) + 1
                )

            confidence = record.get("top_confidence", 0.0)
            if confidence > 0:
                confidence_scores.append(confidence)

        return {
            "total_derivations": len(recent_derivations),
            "intent_distribution": intent_distribution,
            "average_confidence": (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.0
            ),
            "high_confidence_rate": (
                len([c for c in confidence_scores if c > 0.7]) / len(confidence_scores)
                if confidence_scores
                else 0.0
            ),
        }
