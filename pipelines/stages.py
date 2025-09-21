"""
Pipeline Stages - Sub-issue #22.2 Pipeline Integration
======================================================

Common processing stages and utilities for pipeline composition.
Provides reusable components, stage composition, and transformation utilities.

Features:
- Reusable pipeline stage components
- Stage composition and chaining
- Data transformation utilities
- Validation and error handling stages
- Performance monitoring stages
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

# Type variables for generic stage processing
T = TypeVar("T")
R = TypeVar("R")


class StageResult(Enum):
    """Stage execution results."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIP = "skip"
    RETRY = "retry"


@dataclass
class StageContext:
    """Context passed between pipeline stages."""

    stage_id: str
    pipeline_id: str
    operation: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    start_time: float
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    stage_history: Optional[List[str]] = None

    def __post_init__(self):
        if self.stage_history is None:
            self.stage_history = []


@dataclass
class StageExecutionResult:
    """Result of stage execution."""

    stage_id: str
    result: StageResult
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    execution_time: float
    error: Optional[str] = None
    next_stage: Optional[str] = None


class PipelineStage(ABC):
    """
    Abstract base class for all pipeline stages.

    Each stage processes data and passes it to the next stage.
    Stages can be composed to build complex pipeline workflows.
    """

    def __init__(self, stage_id: str, config: Optional[Dict[str, Any]] = None):
        self.stage_id = stage_id
        self.config = config or {}
        self.execution_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0

    @abstractmethod
    async def execute(self, context: StageContext) -> StageExecutionResult:
        """
        Execute the stage logic.

        Args:
            context: Stage execution context with data and metadata

        Returns:
            StageExecutionResult with processed data and execution info
        """
        pass

    async def pre_execute(self, context: StageContext) -> bool:
        """
        Pre-execution hook. Return False to skip stage.

        Args:
            context: Stage execution context

        Returns:
            True to continue execution, False to skip
        """
        return True

    async def post_execute(
        self, context: StageContext, result: StageExecutionResult
    ) -> None:
        """
        Post-execution hook for cleanup or additional processing.

        Args:
            context: Stage execution context
            result: Stage execution result
        """
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """Get stage performance metrics."""
        avg_time = self.total_execution_time / max(self.execution_count, 1)
        return {
            "stage_id": self.stage_id,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.execution_count, 1),
            "average_execution_time": avg_time,
            "total_execution_time": self.total_execution_time,
        }


class ValidationStage(PipelineStage):
    """Stage for data validation and schema checking."""

    def __init__(
        self, stage_id: str = "validation", config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(stage_id, config)
        self.schema_validators = config.get("schema_validators", {}) if config else {}
        self.required_fields = config.get("required_fields", []) if config else []

    async def execute(self, context: StageContext) -> StageExecutionResult:
        """Validate input data against schemas and requirements."""
        start_time = time.time()

        try:
            # Check required fields
            missing_fields = []
            for field in self.required_fields:
                if field not in context.data:
                    missing_fields.append(field)

            if missing_fields:
                return StageExecutionResult(
                    stage_id=self.stage_id,
                    result=StageResult.FAILURE,
                    data=context.data,
                    metadata=context.metadata,
                    execution_time=time.time() - start_time,
                    error=f"Missing required fields: {missing_fields}",
                )

            # Schema validation (basic implementation)
            for field, validator in self.schema_validators.items():
                if field in context.data:
                    value = context.data[field]
                    if not await self._validate_field(field, value, validator):
                        return StageExecutionResult(
                            stage_id=self.stage_id,
                            result=StageResult.FAILURE,
                            data=context.data,
                            metadata=context.metadata,
                            execution_time=time.time() - start_time,
                            error=f"Validation failed for field: {field}",
                        )

            # Validation passed
            return StageExecutionResult(
                stage_id=self.stage_id,
                result=StageResult.SUCCESS,
                data=context.data,
                metadata=context.metadata,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return StageExecutionResult(
                stage_id=self.stage_id,
                result=StageResult.FAILURE,
                data=context.data,
                metadata=context.metadata,
                execution_time=time.time() - start_time,
                error=f"Validation error: {str(e)}",
            )

    async def _validate_field(
        self, field: str, value: Any, validator: Dict[str, Any]
    ) -> bool:
        """Validate a single field against its validator config."""
        # Basic validation implementation
        if "type" in validator:
            expected_type = validator["type"]
            if expected_type == "string" and not isinstance(value, str):
                return False
            elif expected_type == "integer" and not isinstance(value, int):
                return False
            elif expected_type == "list" and not isinstance(value, list):
                return False

        if "min_length" in validator and isinstance(value, (str, list)):
            if len(value) < validator["min_length"]:
                return False

        if "max_length" in validator and isinstance(value, (str, list)):
            if len(value) > validator["max_length"]:
                return False

        return True


class TransformationStage(PipelineStage):
    """Stage for data transformation and mapping."""

    def __init__(
        self, stage_id: str = "transformation", config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(stage_id, config)
        self.transformations = config.get("transformations", {}) if config else {}
        self.field_mappings = config.get("field_mappings", {}) if config else {}

    async def execute(self, context: StageContext) -> StageExecutionResult:
        """Transform data according to configuration."""
        start_time = time.time()

        try:
            transformed_data = context.data.copy()

            # Apply field mappings
            for old_field, new_field in self.field_mappings.items():
                if old_field in transformed_data:
                    transformed_data[new_field] = transformed_data.pop(old_field)

            # Apply transformations
            for field, transformation in self.transformations.items():
                if field in transformed_data:
                    transformed_data[field] = await self._apply_transformation(
                        transformed_data[field], transformation
                    )

            return StageExecutionResult(
                stage_id=self.stage_id,
                result=StageResult.SUCCESS,
                data=transformed_data,
                metadata=context.metadata,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return StageExecutionResult(
                stage_id=self.stage_id,
                result=StageResult.FAILURE,
                data=context.data,
                metadata=context.metadata,
                execution_time=time.time() - start_time,
                error=f"Transformation error: {str(e)}",
            )

    async def _apply_transformation(
        self, value: Any, transformation: Dict[str, Any]
    ) -> Any:
        """Apply a transformation to a value."""
        transform_type = transformation.get("type")

        if transform_type == "uppercase" and isinstance(value, str):
            return value.upper()
        elif transform_type == "lowercase" and isinstance(value, str):
            return value.lower()
        elif transform_type == "trim" and isinstance(value, str):
            return value.strip()
        elif transform_type == "add_prefix" and isinstance(value, str):
            prefix = transformation.get("prefix", "")
            return f"{prefix}{value}"
        elif transform_type == "add_suffix" and isinstance(value, str):
            suffix = transformation.get("suffix", "")
            return f"{value}{suffix}"

        return value


class EnrichmentStage(PipelineStage):
    """Stage for data enrichment and augmentation."""

    def __init__(
        self, stage_id: str = "enrichment", config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(stage_id, config)
        self.enrichment_sources = config.get("enrichment_sources", []) if config else []

    async def execute(self, context: StageContext) -> StageExecutionResult:
        """Enrich data with additional information."""
        start_time = time.time()

        try:
            enriched_data = context.data.copy()
            enriched_metadata = context.metadata.copy()

            # Add standard enrichments
            enriched_metadata.update(
                {
                    "enriched_at": time.time(),
                    "enrichment_stage_id": self.stage_id,
                    "enrichment_version": "1.0.0",
                }
            )

            # Add trace information if available
            if context.trace_id:
                enriched_metadata["trace_id"] = context.trace_id

            if context.correlation_id:
                enriched_metadata["correlation_id"] = context.correlation_id

            # Add pipeline context
            enriched_metadata["pipeline_context"] = {
                "pipeline_id": context.pipeline_id,
                "operation": context.operation,
                "stage_history": (context.stage_history or []) + [self.stage_id],
            }

            # TODO: Add external enrichment source integration
            for source in self.enrichment_sources:
                logger.debug(f"Enriching from source: {source}")
                # Placeholder for external enrichment

            return StageExecutionResult(
                stage_id=self.stage_id,
                result=StageResult.SUCCESS,
                data=enriched_data,
                metadata=enriched_metadata,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return StageExecutionResult(
                stage_id=self.stage_id,
                result=StageResult.FAILURE,
                data=context.data,
                metadata=context.metadata,
                execution_time=time.time() - start_time,
                error=f"Enrichment error: {str(e)}",
            )


class FilteringStage(PipelineStage):
    """Stage for data filtering and conditional processing."""

    def __init__(
        self, stage_id: str = "filtering", config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(stage_id, config)
        self.filter_conditions = config.get("filter_conditions", []) if config else []
        self.filter_mode = (
            config.get("filter_mode", "include") if config else "include"
        )  # include or exclude

    async def execute(self, context: StageContext) -> StageExecutionResult:
        """Filter data based on conditions."""
        start_time = time.time()

        try:
            # Evaluate filter conditions
            should_process = await self._evaluate_conditions(
                context.data, context.metadata
            )

            if self.filter_mode == "exclude":
                should_process = not should_process

            if not should_process:
                return StageExecutionResult(
                    stage_id=self.stage_id,
                    result=StageResult.SKIP,
                    data=context.data,
                    metadata=context.metadata,
                    execution_time=time.time() - start_time,
                )

            return StageExecutionResult(
                stage_id=self.stage_id,
                result=StageResult.SUCCESS,
                data=context.data,
                metadata=context.metadata,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return StageExecutionResult(
                stage_id=self.stage_id,
                result=StageResult.FAILURE,
                data=context.data,
                metadata=context.metadata,
                execution_time=time.time() - start_time,
                error=f"Filtering error: {str(e)}",
            )

    async def _evaluate_conditions(
        self, data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> bool:
        """Evaluate filter conditions against data and metadata."""
        if not self.filter_conditions:
            return True

        for condition in self.filter_conditions:
            field = condition.get("field")
            operator = condition.get("operator", "equals")
            value = condition.get("value")

            if field not in data:
                continue

            field_value = data[field]

            if operator == "equals" and field_value != value:
                return False
            elif operator == "not_equals" and field_value == value:
                return False
            elif (
                operator == "contains"
                and isinstance(field_value, str)
                and value not in field_value
            ):
                return False
            elif operator == "greater_than" and not (
                isinstance(field_value, (int, float)) and field_value > value
            ):
                return False
            elif operator == "less_than" and not (
                isinstance(field_value, (int, float)) and field_value < value
            ):
                return False

        return True


class PipelineStageComposer:
    """Utility for composing multiple stages into a pipeline."""

    def __init__(self, stages: List[PipelineStage]):
        self.stages = stages
        self.execution_history: List[StageExecutionResult] = []

    async def execute_pipeline(
        self, initial_context: StageContext
    ) -> List[StageExecutionResult]:
        """Execute all stages in sequence."""
        current_context = initial_context
        results = []

        for stage in self.stages:
            try:
                # Pre-execute hook
                should_execute = await stage.pre_execute(current_context)
                if not should_execute:
                    logger.debug(
                        f"Skipping stage {stage.stage_id} (pre-execute returned False)"
                    )
                    continue

                # Execute stage
                start_time = time.time()
                result = await stage.execute(current_context)

                # Update stage metrics
                stage.execution_count += 1
                stage.total_execution_time += result.execution_time
                if result.result == StageResult.FAILURE:
                    stage.error_count += 1

                # Post-execute hook
                await stage.post_execute(current_context, result)

                results.append(result)

                # Update context for next stage
                if result.result == StageResult.SUCCESS:
                    current_context.data = result.data
                    current_context.metadata = result.metadata
                    if current_context.stage_history is None:
                        current_context.stage_history = []
                    current_context.stage_history.append(stage.stage_id)
                elif result.result == StageResult.FAILURE:
                    logger.error(f"Stage {stage.stage_id} failed: {result.error}")
                    break
                elif result.result == StageResult.SKIP:
                    logger.debug(f"Stage {stage.stage_id} was skipped")
                    continue

                # Check if stage specified next stage
                if result.next_stage:
                    # Find the next stage by ID
                    next_stage = next(
                        (s for s in self.stages if s.stage_id == result.next_stage),
                        None,
                    )
                    if next_stage:
                        remaining_stages = self.stages[self.stages.index(next_stage) :]
                        composer = PipelineStageComposer(remaining_stages)
                        additional_results = await composer.execute_pipeline(
                            current_context
                        )
                        results.extend(additional_results)
                        break

            except Exception as e:
                logger.error(f"Unexpected error in stage {stage.stage_id}: {e}")
                error_result = StageExecutionResult(
                    stage_id=stage.stage_id,
                    result=StageResult.FAILURE,
                    data=current_context.data,
                    metadata=current_context.metadata,
                    execution_time=(
                        time.time() - start_time if "start_time" in locals() else 0.0
                    ),
                    error=f"Unexpected error: {str(e)}",
                )
                results.append(error_result)
                break

        self.execution_history = results
        return results

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get metrics for the entire pipeline."""
        total_execution_time = sum(r.execution_time for r in self.execution_history)
        successful_stages = len(
            [r for r in self.execution_history if r.result == StageResult.SUCCESS]
        )
        failed_stages = len(
            [r for r in self.execution_history if r.result == StageResult.FAILURE]
        )
        skipped_stages = len(
            [r for r in self.execution_history if r.result == StageResult.SKIP]
        )

        return {
            "total_stages": len(self.stages),
            "executed_stages": len(self.execution_history),
            "successful_stages": successful_stages,
            "failed_stages": failed_stages,
            "skipped_stages": skipped_stages,
            "total_execution_time": total_execution_time,
            "stage_metrics": [stage.get_metrics() for stage in self.stages],
            "execution_history": [
                {
                    "stage_id": r.stage_id,
                    "result": r.result.value,
                    "execution_time": r.execution_time,
                    "error": r.error,
                }
                for r in self.execution_history
            ],
        }


# Convenience factory functions for common stage compositions


def create_basic_processing_pipeline() -> PipelineStageComposer:
    """Create a basic processing pipeline with validation, transformation, and enrichment."""
    stages = [
        ValidationStage("validation"),
        TransformationStage("transformation"),
        EnrichmentStage("enrichment"),
    ]
    return PipelineStageComposer(stages)


def create_data_quality_pipeline() -> PipelineStageComposer:
    """Create a data quality pipeline with validation and filtering."""
    stages = [
        ValidationStage("input_validation"),
        FilteringStage("quality_filter"),
        EnrichmentStage("quality_enrichment"),
    ]
    return PipelineStageComposer(stages)


def create_custom_pipeline(
    stage_configs: List[Dict[str, Any]],
) -> PipelineStageComposer:
    """Create a custom pipeline from stage configurations."""
    stages = []

    for config in stage_configs:
        stage_type = config.get("type")
        stage_id = config.get("id", f"{stage_type}_stage")
        stage_config = config.get("config", {})

        if stage_type == "validation":
            stages.append(ValidationStage(stage_id, stage_config))
        elif stage_type == "transformation":
            stages.append(TransformationStage(stage_id, stage_config))
        elif stage_type == "enrichment":
            stages.append(EnrichmentStage(stage_id, stage_config))
        elif stage_type == "filtering":
            stages.append(FilteringStage(stage_id, stage_config))
        else:
            logger.warning(f"Unknown stage type: {stage_type}")

    return PipelineStageComposer(stages)
