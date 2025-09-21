"""
Pipeline Registry - Sub-issue #22.2 Pipeline Integration
========================================================

Manages pipeline registration, discovery, and health monitoring.
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """Pipeline operational status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PipelineInfo:
    """Pipeline registration information."""

    def __init__(
        self,
        pipeline_id: str,
        pipeline_class: type,
        status: PipelineStatus = PipelineStatus.UNKNOWN,
    ):
        self.pipeline_id = pipeline_id
        self.pipeline_class = pipeline_class
        self.status = status
        self.instance: Optional[Any] = None
        self.last_health_check: Optional[float] = None
        self.failure_count: int = 0
        self.success_count: int = 0

    def is_healthy(self) -> bool:
        """Check if pipeline is healthy enough for use."""
        return self.status in [PipelineStatus.HEALTHY, PipelineStatus.DEGRADED]


class PipelineProtocol(Protocol):
    """Protocol that all pipeline classes must implement."""

    async def run(self, operation: str, payload: Dict[str, Any], **kwargs: Any) -> Any:
        """Execute pipeline operation."""
        ...

    async def health_check(self) -> bool:
        """Check pipeline health."""
        ...


class PipelineRegistry:
    """Registry for managing pipeline instances and their health."""

    def __init__(self):
        self._pipelines: Dict[str, PipelineInfo] = {}
        self._initialize_builtin_pipelines()
        logger.info("PipelineRegistry initialized")

    def _initialize_builtin_pipelines(self):
        """Initialize all built-in P01-P20 pipelines."""
        # Import pipeline classes dynamically
        pipeline_mappings = {
            "P01": ("pipelines.p01", "P01Flow"),
            "P02": ("pipelines.p02", "P02Flow"),
            "P03": ("pipelines.p03", "P03Flow"),
            "P04": ("pipelines.p04", "P04Flow"),
            "P05": ("pipelines.p05", "P05Flow"),
            "P06": ("pipelines.p06", "P06Flow"),
            "P07": ("pipelines.p07", "P07Flow"),
            "P08": ("pipelines.p08", "P08Flow"),
            "P09": ("pipelines.p09", "P09Flow"),
            "P10": ("pipelines.p10", "P10Flow"),
            "P11": ("pipelines.p11", "P11Flow"),
            "P12": ("pipelines.p12", "P12Flow"),
            "P13": ("pipelines.p13", "P13Flow"),
            "P14": ("pipelines.p14", "P14Flow"),
            "P15": ("pipelines.p15", "P15Flow"),
            "P16": ("pipelines.p16", "P16Flow"),
            "P17": ("pipelines.p17", "P17Flow"),
            "P18": ("pipelines.p18", "P18Flow"),
            "P19": ("pipelines.p19", "P19Flow"),
            "P20": ("pipelines.p20", "P20Flow"),
        }

        for pipeline_id, (module_name, class_name) in pipeline_mappings.items():
            try:
                # For now, we'll create mock implementations since the actual pipeline classes are stubs
                # In a full implementation, we'd import the real classes
                mock_pipeline_class = self._create_mock_pipeline_class(pipeline_id)
                self.register(pipeline_id, mock_pipeline_class)
                logger.debug(f"Registered pipeline {pipeline_id}")
            except Exception as e:
                logger.error(f"Failed to register pipeline {pipeline_id}: {e}")

    def _create_mock_pipeline_class(self, pipeline_id: str):
        """Create a mock pipeline class for testing/development."""

        class MockPipelineFlow:
            def __init__(self):
                self.pipeline_id = pipeline_id
                self.execution_count = 0

            async def run(
                self, operation: str, payload: Dict[str, Any], **kwargs: Any
            ) -> Any:
                """Mock pipeline execution."""
                self.execution_count += 1
                await asyncio.sleep(0.01)  # Simulate processing time

                return {
                    "pipeline_id": self.pipeline_id,
                    "operation": operation,
                    "status": "completed",
                    "execution_count": self.execution_count,
                    "result": f"Pipeline {self.pipeline_id} processed {operation}",
                    "payload_processed": bool(payload),
                    "metadata": kwargs,
                }

            async def health_check(self) -> bool:
                """Mock health check."""
                # Simulate occasional health issues for testing
                import random

                return random.random() > 0.05  # 95% success rate

        return MockPipelineFlow

    def register(self, pipeline_id: str, pipeline_class: type) -> None:
        """Register a pipeline in the registry."""
        if pipeline_id in self._pipelines:
            logger.warning(f"Pipeline {pipeline_id} already registered, replacing")

        pipeline_info = PipelineInfo(pipeline_id, pipeline_class)
        self._pipelines[pipeline_id] = pipeline_info
        logger.info(f"Pipeline {pipeline_id} registered successfully")

    def get(self, pipeline_id: str) -> Optional[PipelineInfo]:
        """Get pipeline information by ID."""
        return self._pipelines.get(pipeline_id)

    async def get_instance(self, pipeline_id: str) -> Optional[Any]:
        """Get or create a pipeline instance."""
        pipeline_info = self.get(pipeline_id)
        if not pipeline_info:
            return None

        if pipeline_info.instance is None:
            try:
                pipeline_info.instance = pipeline_info.pipeline_class()
                logger.debug(f"Created new instance for pipeline {pipeline_id}")
            except Exception as e:
                logger.error(
                    f"Failed to create instance for pipeline {pipeline_id}: {e}"
                )
                return None

        return pipeline_info.instance

    async def health_check(self, pipeline_id: str) -> bool:
        """Perform health check on a specific pipeline."""
        pipeline_info = self.get(pipeline_id)
        if not pipeline_info:
            return False

        try:
            instance = await self.get_instance(pipeline_id)
            if not instance:
                pipeline_info.status = PipelineStatus.UNHEALTHY
                return False

            is_healthy = await instance.health_check()

            if is_healthy:
                pipeline_info.status = PipelineStatus.HEALTHY
                pipeline_info.success_count += 1
                pipeline_info.failure_count = 0  # Reset failure count on success
            else:
                pipeline_info.failure_count += 1
                if pipeline_info.failure_count >= 3:
                    pipeline_info.status = PipelineStatus.UNHEALTHY
                else:
                    pipeline_info.status = PipelineStatus.DEGRADED

            pipeline_info.last_health_check = asyncio.get_event_loop().time()
            return is_healthy

        except Exception as e:
            logger.error(f"Health check failed for pipeline {pipeline_id}: {e}")
            pipeline_info.status = PipelineStatus.UNHEALTHY
            pipeline_info.failure_count += 1
            return False

    def list_pipelines(self) -> List[str]:
        """List all registered pipeline IDs."""
        return list(self._pipelines.keys())

    def get_healthy_pipelines(self) -> List[str]:
        """Get list of healthy pipeline IDs."""
        return [
            pipeline_id
            for pipeline_id, info in self._pipelines.items()
            if info.is_healthy()
        ]

    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health checks on all pipelines."""
        results = {}
        for pipeline_id in self._pipelines:
            results[pipeline_id] = await self.health_check(pipeline_id)
        return results


# Global registry instance
pipeline_registry = PipelineRegistry()
