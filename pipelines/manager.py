"""
Pipeline Manager - Sub-issue #22.2 Pipeline Integration
========================================================

Manages pipeline execution, routing, and error handling.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from .registry import pipeline_registry

logger = logging.getLogger(__name__)


class ExecutionStrategy(str, Enum):
    """Pipeline execution strategies."""

    DIRECT = "direct"  # Execute immediately
    QUEUED = "queued"  # Queue for later execution
    BATCH = "batch"  # Batch with similar operations


class ExecutionResult:
    """Result of pipeline execution."""

    def __init__(
        self,
        pipeline_id: str,
        operation: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
    ):
        self.pipeline_id = pipeline_id
        self.operation = operation
        self.success = success
        self.result = result
        self.error = error
        self.execution_time = execution_time
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pipeline_id": self.pipeline_id,
            "operation": self.operation,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
        }


class PipelineManager:
    """Manages pipeline execution with circuit breaker and retry logic."""

    def __init__(self, max_retries: int = 3, circuit_breaker_threshold: int = 5):
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self._execution_history: List[ExecutionResult] = []
        self._circuit_breaker_counts: Dict[str, int] = {}
        logger.info("PipelineManager initialized")

    async def execute(
        self,
        pipeline_id: str,
        operation: str,
        payload: Dict[str, Any],
        strategy: ExecutionStrategy = ExecutionStrategy.DIRECT,
        **kwargs: Any,
    ) -> ExecutionResult:
        """
        Execute a pipeline operation with error handling and circuit breaker.

        Args:
            pipeline_id: The ID of the pipeline to execute
            operation: The operation to perform
            payload: The data payload for the operation
            strategy: Execution strategy (direct, queued, batch)
            **kwargs: Additional parameters

        Returns:
            ExecutionResult containing execution details
        """
        start_time = time.time()

        # Check circuit breaker
        if self._is_circuit_open(pipeline_id):
            error_msg = f"Circuit breaker is open for pipeline {pipeline_id}"
            logger.warning(error_msg)
            return ExecutionResult(
                pipeline_id=pipeline_id,
                operation=operation,
                success=False,
                error=error_msg,
                execution_time=time.time() - start_time,
            )

        # Validate pipeline exists and is healthy
        pipeline_info = pipeline_registry.get(pipeline_id)
        if not pipeline_info:
            error_msg = f"Pipeline {pipeline_id} not found in registry"
            logger.error(error_msg)
            return ExecutionResult(
                pipeline_id=pipeline_id,
                operation=operation,
                success=False,
                error=error_msg,
                execution_time=time.time() - start_time,
            )

        # Check pipeline health
        if not pipeline_info.is_healthy():
            # Try a quick health check to see if it recovered
            is_healthy = await pipeline_registry.health_check(pipeline_id)
            if not is_healthy:
                error_msg = f"Pipeline {pipeline_id} is unhealthy (status: {pipeline_info.status})"
                logger.warning(error_msg)
                return ExecutionResult(
                    pipeline_id=pipeline_id,
                    operation=operation,
                    success=False,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                )

        # Execute based on strategy
        if strategy == ExecutionStrategy.DIRECT:
            return await self._execute_direct(
                pipeline_id, operation, payload, start_time, **kwargs
            )
        elif strategy == ExecutionStrategy.QUEUED:
            return await self._execute_queued(
                pipeline_id, operation, payload, start_time, **kwargs
            )
        elif strategy == ExecutionStrategy.BATCH:
            return await self._execute_batch(
                pipeline_id, operation, payload, start_time, **kwargs
            )
        else:
            error_msg = f"Unknown execution strategy: {strategy}"
            logger.error(error_msg)
            return ExecutionResult(
                pipeline_id=pipeline_id,
                operation=operation,
                success=False,
                error=error_msg,
                execution_time=time.time() - start_time,
            )

    async def _execute_direct(
        self,
        pipeline_id: str,
        operation: str,
        payload: Dict[str, Any],
        start_time: float,
        **kwargs: Any,
    ) -> ExecutionResult:
        """Execute pipeline directly with retry logic."""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # Get pipeline instance
                pipeline_instance = await pipeline_registry.get_instance(pipeline_id)
                if not pipeline_instance:
                    raise RuntimeError(
                        f"Failed to get instance for pipeline {pipeline_id}"
                    )

                # Execute the pipeline
                logger.debug(
                    f"Executing {pipeline_id}.{operation} (attempt {attempt + 1})"
                )
                result = await pipeline_instance.run(operation, payload, **kwargs)

                # Success - record and return
                execution_time = time.time() - start_time
                execution_result = ExecutionResult(
                    pipeline_id=pipeline_id,
                    operation=operation,
                    success=True,
                    result=result,
                    execution_time=execution_time,
                )

                self._record_execution(execution_result)
                self._reset_circuit_breaker(pipeline_id)

                logger.info(
                    f"Pipeline {pipeline_id}.{operation} executed successfully in {execution_time:.3f}s"
                )
                return execution_result

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Pipeline {pipeline_id}.{operation} failed (attempt {attempt + 1}): {e}"
                )

                # Wait before retry (exponential backoff)
                if attempt < self.max_retries:
                    wait_time = 0.1 * (2**attempt)  # 0.1s, 0.2s, 0.4s
                    await asyncio.sleep(wait_time)

        # All retries failed
        execution_time = time.time() - start_time
        execution_result = ExecutionResult(
            pipeline_id=pipeline_id,
            operation=operation,
            success=False,
            error=f"Failed after {self.max_retries + 1} attempts: {last_error}",
            execution_time=execution_time,
        )

        self._record_execution(execution_result)
        self._increment_circuit_breaker(pipeline_id)

        logger.error(
            f"Pipeline {pipeline_id}.{operation} failed permanently: {last_error}"
        )
        return execution_result

    async def _execute_queued(
        self,
        pipeline_id: str,
        operation: str,
        payload: Dict[str, Any],
        start_time: float,
        **kwargs: Any,
    ) -> ExecutionResult:
        """Execute pipeline with queuing (stub for future implementation)."""
        # For now, just execute directly
        logger.debug(
            f"Queued execution not yet implemented, executing directly: {pipeline_id}.{operation}"
        )
        return await self._execute_direct(
            pipeline_id, operation, payload, start_time, **kwargs
        )

    async def _execute_batch(
        self,
        pipeline_id: str,
        operation: str,
        payload: Dict[str, Any],
        start_time: float,
        **kwargs: Any,
    ) -> ExecutionResult:
        """Execute pipeline with batching (stub for future implementation)."""
        # For now, just execute directly
        logger.debug(
            f"Batch execution not yet implemented, executing directly: {pipeline_id}.{operation}"
        )
        return await self._execute_direct(
            pipeline_id, operation, payload, start_time, **kwargs
        )

    def _is_circuit_open(self, pipeline_id: str) -> bool:
        """Check if circuit breaker is open for a pipeline."""
        failure_count = self._circuit_breaker_counts.get(pipeline_id, 0)
        return failure_count >= self.circuit_breaker_threshold

    def _increment_circuit_breaker(self, pipeline_id: str) -> None:
        """Increment circuit breaker failure count."""
        current_count = self._circuit_breaker_counts.get(pipeline_id, 0)
        self._circuit_breaker_counts[pipeline_id] = current_count + 1

        if self._circuit_breaker_counts[pipeline_id] >= self.circuit_breaker_threshold:
            logger.warning(f"Circuit breaker opened for pipeline {pipeline_id}")

    def _reset_circuit_breaker(self, pipeline_id: str) -> None:
        """Reset circuit breaker for successful execution."""
        if pipeline_id in self._circuit_breaker_counts:
            del self._circuit_breaker_counts[pipeline_id]

    def _record_execution(self, result: ExecutionResult) -> None:
        """Record execution result in history."""
        self._execution_history.append(result)

        # Keep only recent history (last 1000 executions)
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-1000:]

    def get_execution_stats(self, pipeline_id: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics."""
        relevant_executions = self._execution_history
        if pipeline_id:
            relevant_executions = [
                e for e in self._execution_history if e.pipeline_id == pipeline_id
            ]

        if not relevant_executions:
            return {"total_executions": 0}

        total = len(relevant_executions)
        successful = sum(1 for e in relevant_executions if e.success)
        failed = total - successful
        avg_execution_time = sum(e.execution_time for e in relevant_executions) / total

        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "average_execution_time": avg_execution_time,
            "circuit_breaker_failures": (
                self._circuit_breaker_counts.get(pipeline_id, 0)
                if pipeline_id
                else dict(self._circuit_breaker_counts)
            ),
        }

    async def health_check_all_pipelines(self) -> Dict[str, bool]:
        """Health check all pipelines via registry."""
        return await pipeline_registry.health_check_all()


# Global manager instance
pipeline_manager = PipelineManager()
