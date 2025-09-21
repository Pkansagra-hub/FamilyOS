"""
Feature Flag Manager
===================

Main interface for feature flag operations in MemoryOS.
Provides high-level API for flag evaluation, configuration management,
and cognitive-aware feature control.
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .config import (
    DEFAULT_COGNITIVE_FLAGS,
    ConfigLoader,
    Environment,
    FlagConfig,
    FlagDefinition,
)
from .evaluator import EvaluationContext, EvaluationResult, FlagEvaluator


class FeatureFlagManager:
    """
    Central manager for feature flag operations.

    Provides the main interface for:
    - Flag evaluation with cognitive awareness
    - Configuration management and hot-reloading
    - Performance monitoring and statistics
    - Integration with MemoryOS cognitive systems
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        environment: Environment = Environment.DEVELOPMENT,
        enable_hot_reload: bool = True,
    ):
        self.environment = environment
        self.config_path = config_path
        self.enable_hot_reload = enable_hot_reload

        # Core components
        self.config: Optional[FlagConfig] = None
        self.evaluator: Optional[FlagEvaluator] = None
        self.config_loader = ConfigLoader()

        # Hot reload tracking
        self.last_config_mtime: Optional[float] = None
        self.reload_check_interval = 5.0  # seconds
        self.reload_task: Optional[asyncio.Task] = None

        # Performance tracking
        self.manager_stats = {
            "flags_evaluated": 0,
            "config_reloads": 0,
            "hot_reload_errors": 0,
            "last_reload_time": None,
        }

        # Change notifications
        self.change_callbacks: List[Any] = []

    async def initialize(self) -> None:
        """Initialize the feature flag manager."""
        await self.load_config()

        if self.enable_hot_reload and self.config_path:
            self.reload_task = asyncio.create_task(self._hot_reload_loop())

    async def shutdown(self) -> None:
        """Gracefully shutdown the manager."""
        if self.reload_task:
            self.reload_task.cancel()
            try:
                await self.reload_task
            except asyncio.CancelledError:
                pass

    async def load_config(self, config_path: Optional[Path] = None) -> None:
        """Load or reload configuration."""
        target_path = config_path or self.config_path

        if target_path and target_path.exists():
            self.config = ConfigLoader.load_from_yaml(target_path)
            self.last_config_mtime = target_path.stat().st_mtime
        else:
            # Use default configuration with cognitive flags
            self.config = FlagConfig()
            for flag_name, flag in DEFAULT_COGNITIVE_FLAGS.items():
                self.config.add_flag(flag)

        # Create evaluator with new config
        if self.config:
            self.evaluator = FlagEvaluator(self.config)
        self.manager_stats["config_reloads"] += 1
        self.manager_stats["last_reload_time"] = time.time()

        # Notify change callbacks
        await self._notify_config_changed()

    async def is_enabled(
        self, flag_name: str, context: Optional[EvaluationContext] = None
    ) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: Name of the flag to check
            context: Evaluation context (created if None)

        Returns:
            True if flag is enabled, False otherwise
        """
        if not self.evaluator:
            return False

        if context is None:
            context = self.create_context()

        result = await self.evaluator.evaluate_flag(flag_name, context)
        self.manager_stats["flags_evaluated"] += 1

        return bool(result.value)

    async def get_flag_value(
        self,
        flag_name: str,
        default_value: Any = False,
        context: Optional[EvaluationContext] = None,
    ) -> Any:
        """
        Get the value of a feature flag.

        Args:
            flag_name: Name of the flag
            default_value: Value to return if flag not found
            context: Evaluation context

        Returns:
            Flag value or default_value
        """
        if not self.evaluator:
            return default_value

        if context is None:
            context = self.create_context()

        result = await self.evaluator.evaluate_flag(flag_name, context)
        self.manager_stats["flags_evaluated"] += 1

        if result.rule_applied == "flag_not_found":
            return default_value

        return result.value

    async def get_flag_details(
        self, flag_name: str, context: Optional[EvaluationContext] = None
    ) -> Optional[EvaluationResult]:
        """
        Get detailed evaluation result for a flag.

        Args:
            flag_name: Name of the flag
            context: Evaluation context

        Returns:
            EvaluationResult with full details
        """
        if not self.evaluator:
            return None

        if context is None:
            context = self.create_context()

        result = await self.evaluator.evaluate_flag(flag_name, context)
        self.manager_stats["flags_evaluated"] += 1

        return result

    async def get_flags_by_category(
        self, category: str, context: Optional[EvaluationContext] = None
    ) -> Dict[str, bool]:
        """
        Get all enabled flags in a category.

        Args:
            category: Flag category to filter by
            context: Evaluation context

        Returns:
            Dict mapping flag names to enabled status
        """
        if not self.evaluator:
            return {}

        if context is None:
            context = self.create_context()

        results = await self.evaluator.get_flags_by_category(category, context)
        self.manager_stats["flags_evaluated"] += len(results)

        return {name: bool(result.value) for name, result in results.items()}

    async def get_cognitive_flags(
        self, context: Optional[EvaluationContext] = None
    ) -> Dict[str, bool]:
        """
        Get all cognitive-aware flags with their values.

        Args:
            context: Evaluation context with cognitive state

        Returns:
            Dict mapping cognitive flag names to values
        """
        if not self.evaluator:
            return {}

        if context is None:
            context = self.create_context()

        results = await self.evaluator.get_cognitive_flags(context)
        self.manager_stats["flags_evaluated"] += len(results)

        return {name: bool(result.value) for name, result in results.items()}

    def create_context(
        self,
        cognitive_load: float = 0.0,
        working_memory_load: float = 0.0,
        attention_queue_depth: int = 0,
        neural_pathway: Optional[str] = None,
        brain_region: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> EvaluationContext:
        """
        Create evaluation context for flag evaluation.

        Args:
            cognitive_load: Current cognitive load (0.0-1.0)
            working_memory_load: Working memory utilization (0.0-1.0)
            attention_queue_depth: Number of items in attention queue
            neural_pathway: Active neural pathway identifier
            brain_region: Current brain region being processed
            user_id: User identifier
            session_id: Session identifier
            request_id: Request identifier
            trace_id: Trace identifier

        Returns:
            EvaluationContext for flag evaluation
        """
        return EvaluationContext(
            environment=self.environment,
            cognitive_load=cognitive_load,
            working_memory_load=working_memory_load,
            attention_queue_depth=attention_queue_depth,
            neural_pathway=neural_pathway,
            brain_region=brain_region,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            trace_id=trace_id,
        )

    def get_available_flags(self) -> Dict[str, FlagDefinition]:
        """Get all available flag definitions."""
        if not self.config:
            return {}
        return self.config.flags.copy()

    def get_flags_by_category_definition(
        self, category: str
    ) -> Dict[str, FlagDefinition]:
        """Get flag definitions for a specific category."""
        if not self.config:
            return {}
        return self.config.get_flags_by_category(category)

    def get_cognitive_flag_definitions(self) -> Dict[str, FlagDefinition]:
        """Get all cognitive-aware flag definitions."""
        if not self.config:
            return {}
        return self.config.get_cognitive_flags()

    def get_categories(self) -> Set[str]:
        """Get all available flag categories."""
        if not self.config:
            return set()
        return {flag.category for flag in self.config.flags.values()}

    async def validate_config(self) -> Dict[str, Any]:
        """
        Validate current configuration.

        Returns:
            Validation report with errors and warnings
        """
        if not self.config:
            return {"valid": False, "error": "No configuration loaded"}

        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "flag_count": len(self.config.flags),
            "categories": list(self.get_categories()),
            "cognitive_flags": len(self.get_cognitive_flag_definitions()),
        }

        # Validate each flag
        for flag_name, flag in self.config.flags.items():
            try:
                # Check if flag has valid environments
                for env in Environment:
                    flag.get_value(env)

                # Validate cognitive context if present
                if flag.is_cognitive_aware() and flag.cognitive_context:
                    if hasattr(flag.cognitive_context, "cognitive_load_threshold"):
                        if flag.cognitive_context.cognitive_load_threshold > 1.0:
                            validation_result["warnings"].append(
                                f"Flag {flag_name}: cognitive_load_threshold > 1.0"
                            )

            except Exception as e:
                validation_result["errors"].append(f"Flag {flag_name}: {str(e)}")
                validation_result["valid"] = False

        return validation_result

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {
            "manager": self.manager_stats.copy(),
            "evaluator": (
                self.evaluator.get_evaluation_stats() if self.evaluator else {}
            ),
            "config": {
                "flags_loaded": len(self.config.flags) if self.config else 0,
                "categories": len(self.get_categories()),
                "cognitive_flags": len(self.get_cognitive_flag_definitions()),
            },
        }

        return stats

    def add_change_callback(self, callback: Any) -> None:
        """Add callback to be notified of configuration changes."""
        self.change_callbacks.append(callback)

    def remove_change_callback(self, callback: Any) -> None:
        """Remove configuration change callback."""
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)

    async def force_reload(self) -> bool:
        """Force reload configuration from disk."""
        try:
            await self.load_config()
            return True
        except Exception:
            self.manager_stats["hot_reload_errors"] += 1
            # Log error (would integrate with observability system)
            return False

    async def _hot_reload_loop(self) -> None:
        """Background task for hot-reloading configuration."""
        while True:
            try:
                await asyncio.sleep(self.reload_check_interval)

                if self.config_path and self.config_path.exists():
                    current_mtime = self.config_path.stat().st_mtime

                    if (
                        self.last_config_mtime is None
                        or current_mtime > self.last_config_mtime
                    ):
                        await self.load_config()

            except asyncio.CancelledError:
                break
            except Exception:
                self.manager_stats["hot_reload_errors"] += 1
                # Log error (would integrate with observability system)
                await asyncio.sleep(self.reload_check_interval)

    async def _notify_config_changed(self) -> None:
        """Notify all change callbacks of configuration update."""
        for callback in self.change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception:
                # Log error (would integrate with observability system)
                pass


# Global manager instance (initialized by application)
_global_manager: Optional[FeatureFlagManager] = None


async def initialize_global_manager(
    config_path: Optional[Path] = None,
    environment: Environment = Environment.DEVELOPMENT,
    enable_hot_reload: bool = True,
) -> FeatureFlagManager:
    """Initialize the global feature flag manager."""
    global _global_manager

    _global_manager = FeatureFlagManager(
        config_path=config_path,
        environment=environment,
        enable_hot_reload=enable_hot_reload,
    )

    await _global_manager.initialize()
    return _global_manager


def get_global_manager() -> Optional[FeatureFlagManager]:
    """Get the global feature flag manager instance."""
    return _global_manager


async def is_enabled(
    flag_name: str, context: Optional[EvaluationContext] = None
) -> bool:
    """Convenience function to check if a flag is enabled using global manager."""
    if _global_manager:
        return await _global_manager.is_enabled(flag_name, context)
    return False


async def get_flag_value(
    flag_name: str,
    default_value: Any = False,
    context: Optional[EvaluationContext] = None,
) -> Any:
    """Convenience function to get flag value using global manager."""
    if _global_manager:
        return await _global_manager.get_flag_value(flag_name, default_value, context)
    return default_value


def create_context(**kwargs) -> EvaluationContext:
    """Convenience function to create evaluation context."""
    if _global_manager:
        return _global_manager.create_context(**kwargs)
    return EvaluationContext(**kwargs)
