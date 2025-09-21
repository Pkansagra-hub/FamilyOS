"""Advanced event filtering system with JSONPath and custom filter functions.

This module extends the subscription system with sophisticated event filtering
capabilities including JSONPath expressions, custom filter functions, and
complex boolean logic for event matching.

Architecture:
- FilterExpression: Abstract base for filter expressions
- JSONPathFilter: JSONPath-based content filtering
- CustomFunctionFilter: User-defined filter functions
- CompoundFilter: Boolean logic for combining filters
- FilterManager: Manages filter registration and evaluation

Features:
- JSONPath expressions for deep content filtering
- Custom filter function registration
- Boolean logic (AND, OR, NOT) for combining filters
- Performance optimized filter evaluation
- Filter validation and error handling
- Subscription-level filter management

Example:
    >>> # JSONPath filter
    >>> filter1 = JSONPathFilter("$.payload.priority", "high")
    >>>
    >>> # Custom function filter
    >>> def user_filter(event):
    >>>     return event.actor.get('user_type') == 'admin'
    >>> filter2 = CustomFunctionFilter(user_filter)
    >>>
    >>> # Compound filter
    >>> compound = CompoundFilter("AND", [filter1, filter2])
    >>> subscription.add_filter(compound)
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .types import Event

logger = logging.getLogger(__name__)


class FilterError(Exception):
    """Base exception for filter-related errors."""

    pass


class FilterValidationError(FilterError):
    """Exception raised when filter validation fails."""

    pass


class FilterEvaluationError(FilterError):
    """Exception raised during filter evaluation."""

    pass


@dataclass
class FilterResult:
    """Result of filter evaluation."""

    matches: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class FilterExpression(ABC):
    """Abstract base class for filter expressions."""

    @property
    @abstractmethod
    def filter_type(self) -> str:
        """Type identifier for this filter."""
        pass

    @abstractmethod
    def evaluate(self, event: Event) -> FilterResult:
        """
        Evaluate the filter against an event.

        Args:
            event: Event to evaluate

        Returns:
            FilterResult with match result and metadata
        """
        pass

    @abstractmethod
    def validate(self) -> None:
        """
        Validate the filter configuration.

        Raises:
            FilterValidationError: If filter configuration is invalid
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary representation."""
        return {"type": self.filter_type, "config": self._get_config()}

    @abstractmethod
    def _get_config(self) -> Dict[str, Any]:
        """Get filter-specific configuration."""
        pass


class SimpleFilter(FilterExpression):
    """Simple field-based filtering with exact or pattern matching."""

    def __init__(
        self,
        field_path: str,
        expected_value: Any,
        match_type: str = "exact",  # exact, regex, contains, gt, lt, gte, lte
    ):
        """
        Initialize simple filter.

        Args:
            field_path: Dot-notation path to field (e.g., "payload.priority")
            expected_value: Value to match against
            match_type: Type of matching to perform
        """
        self.field_path = field_path
        self.expected_value = expected_value
        self.match_type = match_type
        self.validate()

    @property
    def filter_type(self) -> str:
        return "simple"

    def evaluate(self, event: Event) -> FilterResult:
        """Evaluate simple filter against event."""
        import time

        start_time = time.time()

        try:
            # Extract field value using dot notation
            field_value = self._get_field_value(event, self.field_path)

            # Perform matching based on match_type
            matches = self._matches_value(
                field_value, self.expected_value, self.match_type
            )

            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                matches=matches,
                execution_time_ms=execution_time,
                metadata={
                    "field_path": self.field_path,
                    "field_value": field_value,
                    "expected_value": self.expected_value,
                    "match_type": self.match_type,
                },
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Simple filter evaluation failed: {e}")

            return FilterResult(
                matches=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"field_path": self.field_path},
            )

    def validate(self) -> None:
        """Validate simple filter configuration."""
        if not self.field_path:
            raise FilterValidationError("Field path cannot be empty")

        valid_match_types = ["exact", "regex", "contains", "gt", "lt", "gte", "lte"]
        if self.match_type not in valid_match_types:
            raise FilterValidationError(f"Invalid match_type: {self.match_type}")

        if self.match_type == "regex":
            try:
                re.compile(str(self.expected_value))
            except re.error as e:
                raise FilterValidationError(f"Invalid regex pattern: {e}")

    def _get_config(self) -> Dict[str, Any]:
        return {
            "field_path": self.field_path,
            "expected_value": self.expected_value,
            "match_type": self.match_type,
        }

    def _get_field_value(self, event: Event, field_path: str) -> Any:
        """Extract field value using dot notation."""
        # Convert event to dict for easier access
        if hasattr(event, "__dict__"):
            event_dict = event.__dict__
        else:
            # Fallback for other event types
            event_dict = {"event": event}

        # Navigate the field path
        current = event_dict
        for part in field_path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                # Try to access as attribute
                current = getattr(current, part, None)

            if current is None:
                break

        return current

    def _matches_value(
        self, field_value: Any, expected_value: Any, match_type: str
    ) -> bool:
        """Check if field value matches expected value based on match type."""
        if field_value is None:
            return expected_value is None

        if match_type == "exact":
            return field_value == expected_value

        elif match_type == "contains":
            return str(expected_value) in str(field_value)

        elif match_type == "regex":
            try:
                return bool(re.search(str(expected_value), str(field_value)))
            except re.error:
                return False

        elif match_type in ["gt", "lt", "gte", "lte"]:
            try:
                field_num = float(field_value)
                expected_num = float(expected_value)

                if match_type == "gt":
                    return field_num > expected_num
                elif match_type == "lt":
                    return field_num < expected_num
                elif match_type == "gte":
                    return field_num >= expected_num
                elif match_type == "lte":
                    return field_num <= expected_num
            except (ValueError, TypeError):
                return False

        return False


class JSONPathFilter(FilterExpression):
    """JSONPath-based content filtering for complex event data."""

    def __init__(
        self, jsonpath_expr: str, expected_value: Any, match_type: str = "exact"
    ):
        """
        Initialize JSONPath filter.

        Args:
            jsonpath_expr: JSONPath expression (e.g., "$.payload.items[*].status")
            expected_value: Value to match against
            match_type: Type of matching (exact, contains, regex, any, all)
        """
        self.jsonpath_expr = jsonpath_expr
        self.expected_value = expected_value
        self.match_type = match_type
        self.validate()

    @property
    def filter_type(self) -> str:
        return "jsonpath"

    def evaluate(self, event: Event) -> FilterResult:
        """Evaluate JSONPath filter against event."""
        import time

        start_time = time.time()

        try:
            # Convert event to JSON-serializable format
            event_data = self._event_to_dict(event)

            # Apply JSONPath expression (simplified implementation)
            extracted_values = self._apply_jsonpath(event_data, self.jsonpath_expr)

            # Check matches based on match_type
            matches = self._check_matches(
                extracted_values, self.expected_value, self.match_type
            )

            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                matches=matches,
                execution_time_ms=execution_time,
                metadata={
                    "jsonpath_expr": self.jsonpath_expr,
                    "extracted_values": extracted_values,
                    "expected_value": self.expected_value,
                    "match_type": self.match_type,
                },
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"JSONPath filter evaluation failed: {e}")

            return FilterResult(
                matches=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"jsonpath_expr": self.jsonpath_expr},
            )

    def validate(self) -> None:
        """Validate JSONPath filter configuration."""
        if not self.jsonpath_expr:
            raise FilterValidationError("JSONPath expression cannot be empty")

        if not self.jsonpath_expr.startswith("$"):
            raise FilterValidationError("JSONPath expression must start with '$'")

        valid_match_types = ["exact", "contains", "regex", "any", "all"]
        if self.match_type not in valid_match_types:
            raise FilterValidationError(f"Invalid match_type: {self.match_type}")

    def _get_config(self) -> Dict[str, Any]:
        return {
            "jsonpath_expr": self.jsonpath_expr,
            "expected_value": self.expected_value,
            "match_type": self.match_type,
        }

    def _event_to_dict(self, event: Event) -> Dict[str, Any]:
        """Convert event to dictionary for JSONPath processing."""
        if hasattr(event, "to_dict"):
            return event.to_dict()
        elif hasattr(event, "__dict__"):
            return event.__dict__
        else:
            return {"event": str(event)}

    def _apply_jsonpath(self, data: Dict[str, Any], jsonpath_expr: str) -> List[Any]:
        """
        Apply JSONPath expression to data (simplified implementation).

        Note: This is a basic implementation. For production, consider using
        a dedicated JSONPath library like jsonpath-ng.
        """
        # Remove the root '$' and split the path
        path_parts = (
            jsonpath_expr[1:].split(".")
            if jsonpath_expr.startswith("$.")
            else [jsonpath_expr]
        )

        results = [data]

        for part in path_parts:
            if not part:
                continue

            new_results = []
            for current_data in results:
                if isinstance(current_data, dict):
                    if part in current_data:
                        new_results.append(current_data[part])
                elif isinstance(current_data, list):
                    # Handle array access like [*] or [0]
                    if part == "*":
                        new_results.extend(current_data)
                    elif part.isdigit():
                        idx = int(part)
                        if 0 <= idx < len(current_data):
                            new_results.append(current_data[idx])

            results = new_results
            if not results:
                break

        return results

    def _check_matches(
        self, extracted_values: List[Any], expected_value: Any, match_type: str
    ) -> bool:
        """Check if extracted values match expected value."""
        if not extracted_values:
            return expected_value is None

        if match_type == "exact":
            return expected_value in extracted_values

        elif match_type == "contains":
            return any(str(expected_value) in str(val) for val in extracted_values)

        elif match_type == "regex":
            try:
                pattern = re.compile(str(expected_value))
                return any(pattern.search(str(val)) for val in extracted_values)
            except re.error:
                return False

        elif match_type == "any":
            # At least one value matches
            return any(val == expected_value for val in extracted_values)

        elif match_type == "all":
            # All values match
            return all(val == expected_value for val in extracted_values)

        return False


class CustomFunctionFilter(FilterExpression):
    """Filter using custom user-defined functions."""

    def __init__(self, filter_function: Callable[[Event], bool], name: str = "custom"):
        """
        Initialize custom function filter.

        Args:
            filter_function: Function that takes Event and returns bool
            name: Name identifier for this filter function
        """
        self.filter_function = filter_function
        self.name = name
        self.validate()

    @property
    def filter_type(self) -> str:
        return "custom_function"

    def evaluate(self, event: Event) -> FilterResult:
        """Evaluate custom function filter against event."""
        import time

        start_time = time.time()

        try:
            matches = self.filter_function(event)
            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                matches=bool(matches),
                execution_time_ms=execution_time,
                metadata={
                    "function_name": self.name,
                    "function": str(self.filter_function),
                },
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Custom function filter '{self.name}' failed: {e}")

            return FilterResult(
                matches=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"function_name": self.name},
            )

    def validate(self) -> None:
        """Validate custom function filter."""
        if not callable(self.filter_function):
            raise FilterValidationError("Filter function must be callable")

        if not self.name:
            raise FilterValidationError("Filter name cannot be empty")

    def _get_config(self) -> Dict[str, Any]:
        return {"function_name": self.name, "function_repr": str(self.filter_function)}


class CompoundFilter(FilterExpression):
    """Boolean logic for combining multiple filters."""

    def __init__(
        self,
        operator: str,  # AND, OR, NOT
        filters: List[FilterExpression],
        name: str = "compound",
    ):
        """
        Initialize compound filter.

        Args:
            operator: Boolean operator (AND, OR, NOT)
            filters: List of filters to combine
            name: Name identifier for this compound filter
        """
        self.operator = operator.upper()
        self.filters = filters
        self.name = name
        self.validate()

    @property
    def filter_type(self) -> str:
        return "compound"

    def evaluate(self, event: Event) -> FilterResult:
        """Evaluate compound filter against event."""
        import time

        start_time = time.time()

        try:
            # Evaluate all sub-filters
            sub_results = []
            for filter_expr in self.filters:
                result = filter_expr.evaluate(event)
                sub_results.append(result)

            # Apply boolean logic
            if self.operator == "AND":
                matches = all(result.matches for result in sub_results)
            elif self.operator == "OR":
                matches = any(result.matches for result in sub_results)
            elif self.operator == "NOT":
                if len(sub_results) != 1:
                    raise FilterEvaluationError(
                        "NOT operator requires exactly one filter"
                    )
                matches = not sub_results[0].matches
            else:
                raise FilterEvaluationError(f"Unsupported operator: {self.operator}")

            execution_time = (time.time() - start_time) * 1000

            return FilterResult(
                matches=matches,
                execution_time_ms=execution_time,
                metadata={
                    "operator": self.operator,
                    "sub_filter_count": len(sub_results),
                    "sub_results": [
                        {"matches": r.matches, "error": r.error} for r in sub_results
                    ],
                },
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Compound filter evaluation failed: {e}")

            return FilterResult(
                matches=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"operator": self.operator},
            )

    def validate(self) -> None:
        """Validate compound filter configuration."""
        valid_operators = ["AND", "OR", "NOT"]
        if self.operator not in valid_operators:
            raise FilterValidationError(f"Invalid operator: {self.operator}")

        if self.operator == "NOT" and len(self.filters) != 1:
            raise FilterValidationError("NOT operator requires exactly one filter")

        if len(self.filters) == 0:
            raise FilterValidationError(
                "Compound filter requires at least one sub-filter"
            )

        # Validate all sub-filters
        for filter_expr in self.filters:
            filter_expr.validate()

    def _get_config(self) -> Dict[str, Any]:
        return {
            "operator": self.operator,
            "name": self.name,
            "filters": [f.to_dict() for f in self.filters],
        }


class FilterManager:
    """Manages filter registration and evaluation for subscriptions."""

    def __init__(self):
        """Initialize the filter manager."""
        self._registered_functions: Dict[str, Callable[[Event], bool]] = {}
        self._filter_stats = {
            "total_evaluations": 0,
            "successful_evaluations": 0,
            "failed_evaluations": 0,
            "average_execution_time_ms": 0.0,
        }

    def register_function(
        self, name: str, filter_function: Callable[[Event], bool]
    ) -> None:
        """
        Register a custom filter function.

        Args:
            name: Unique name for the function
            filter_function: Function that takes Event and returns bool
        """
        if not callable(filter_function):
            raise FilterValidationError("Filter function must be callable")

        self._registered_functions[name] = filter_function
        logger.info(f"Registered filter function: {name}")

    def unregister_function(self, name: str) -> bool:
        """
        Unregister a custom filter function.

        Args:
            name: Name of function to unregister

        Returns:
            True if function was removed, False if not found
        """
        if name in self._registered_functions:
            del self._registered_functions[name]
            logger.info(f"Unregistered filter function: {name}")
            return True
        return False

    def get_function(self, name: str) -> Optional[Callable[[Event], bool]]:
        """Get registered filter function by name."""
        return self._registered_functions.get(name)

    def list_functions(self) -> List[str]:
        """List all registered filter function names."""
        return list(self._registered_functions.keys())

    def create_filter(self, filter_config: Dict[str, Any]) -> FilterExpression:
        """
        Create filter from configuration dictionary.

        Args:
            filter_config: Filter configuration

        Returns:
            FilterExpression instance

        Raises:
            FilterValidationError: If configuration is invalid
        """
        filter_type = filter_config.get("type")
        config = filter_config.get("config", {})

        if filter_type == "simple":
            return SimpleFilter(
                field_path=config["field_path"],
                expected_value=config["expected_value"],
                match_type=config.get("match_type", "exact"),
            )

        elif filter_type == "jsonpath":
            return JSONPathFilter(
                jsonpath_expr=config["jsonpath_expr"],
                expected_value=config["expected_value"],
                match_type=config.get("match_type", "exact"),
            )

        elif filter_type == "custom_function":
            function_name = config["function_name"]
            filter_function = self.get_function(function_name)
            if not filter_function:
                raise FilterValidationError(
                    f"Filter function not found: {function_name}"
                )

            return CustomFunctionFilter(filter_function, function_name)

        elif filter_type == "compound":
            sub_filters = [
                self.create_filter(sub_config) for sub_config in config["filters"]
            ]
            return CompoundFilter(
                operator=config["operator"],
                filters=sub_filters,
                name=config.get("name", "compound"),
            )

        else:
            raise FilterValidationError(f"Unknown filter type: {filter_type}")

    def evaluate_filters(
        self, filters: List[FilterExpression], event: Event
    ) -> FilterResult:
        """
        Evaluate multiple filters against an event.

        Args:
            filters: List of filters to evaluate
            event: Event to evaluate against

        Returns:
            FilterResult with combined evaluation result
        """
        import time

        start_time = time.time()

        try:
            # If no filters, match everything
            if not filters:
                return FilterResult(matches=True, execution_time_ms=0.0)

            # Evaluate all filters (AND logic by default)
            all_results = []
            for filter_expr in filters:
                result = filter_expr.evaluate(event)
                all_results.append(result)

                # Short-circuit on first failure
                if not result.matches:
                    break

            # Calculate overall result
            matches = all(result.matches for result in all_results)
            execution_time = (time.time() - start_time) * 1000

            # Update statistics
            self._filter_stats["total_evaluations"] += 1
            if matches:
                self._filter_stats["successful_evaluations"] += 1
            else:
                self._filter_stats["failed_evaluations"] += 1

            # Update average execution time
            total_evals = self._filter_stats["total_evaluations"]
            current_avg = self._filter_stats["average_execution_time_ms"]
            new_avg = ((current_avg * (total_evals - 1)) + execution_time) / total_evals
            self._filter_stats["average_execution_time_ms"] = new_avg

            return FilterResult(
                matches=matches,
                execution_time_ms=execution_time,
                metadata={
                    "filter_count": len(filters),
                    "results": [
                        {
                            "type": type(f).__name__,
                            "matches": r.matches,
                            "error": r.error,
                        }
                        for f, r in zip(filters, all_results)
                    ],
                },
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Filter evaluation failed: {e}")

            self._filter_stats["total_evaluations"] += 1
            self._filter_stats["failed_evaluations"] += 1

            return FilterResult(
                matches=False, error=str(e), execution_time_ms=execution_time
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get filter evaluation statistics."""
        stats = self._filter_stats.copy()
        stats["registered_functions"] = len(self._registered_functions)

        if stats["total_evaluations"] > 0:
            stats["success_rate"] = (
                stats["successful_evaluations"] / stats["total_evaluations"]
            )
        else:
            stats["success_rate"] = 0.0

        return stats


# Global filter manager instance
_default_filter_manager: Optional[FilterManager] = None


def get_filter_manager() -> FilterManager:
    """Get the global filter manager instance."""
    global _default_filter_manager
    if _default_filter_manager is None:
        _default_filter_manager = FilterManager()

        # Register some common filter functions
        _default_filter_manager.register_function(
            "is_high_priority",
            lambda event: getattr(event, "priority", "normal") == "high",
        )

        _default_filter_manager.register_function(
            "is_error_event", lambda event: "error" in str(event).lower()
        )

    return _default_filter_manager


def set_filter_manager(manager: FilterManager) -> None:
    """Set the global filter manager (mainly for testing)."""
    global _default_filter_manager
    _default_filter_manager = manager
