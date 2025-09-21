"""
Adaptive Learning Engine
========================

Brain-inspired adaptive learning for MemoryOS feature flag optimization.
Provides neural network-inspired learning algorithms that adapt flag thresholds
and decision parameters based on cognitive performance patterns.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..flag_manager import CognitiveFlagContext, CognitiveFlagManager
from .neural_correlator import BrainRegion, NeuralPathway


class LearningAlgorithm(Enum):
    """Types of learning algorithms."""

    HEBBIAN = "hebbian"  # Neurons that fire together, wire together
    REINFORCEMENT = "reinforcement"  # Reward-based learning
    GRADIENT_DESCENT = "gradient_descent"  # Gradient-based optimization
    GENETIC = "genetic"  # Evolutionary optimization
    NEURAL_PLASTICITY = "neural_plasticity"  # Synaptic strength adaptation


class OptimizationTarget(Enum):
    """Optimization targets for adaptive learning."""

    PERFORMANCE = "performance"  # Optimize for speed/efficiency
    ACCURACY = "accuracy"  # Optimize for correctness
    COGNITIVE_EFFICIENCY = "cognitive_efficiency"  # Optimize cognitive load
    BALANCED = "balanced"  # Balance multiple objectives
    USER_EXPERIENCE = "user_experience"  # Optimize for user satisfaction


@dataclass
class LearningParameters:
    """Parameters for adaptive learning algorithms."""

    # Learning rates
    learning_rate: float = 0.01
    decay_rate: float = 0.95
    momentum: float = 0.9

    # Exploration parameters
    exploration_rate: float = 0.1
    exploration_decay: float = 0.99
    min_exploration_rate: float = 0.01

    # Memory parameters
    memory_size: int = 1000
    forgetting_rate: float = 0.05
    consolidation_threshold: float = 0.7

    # Convergence parameters
    convergence_threshold: float = 0.001
    max_iterations: int = 1000
    patience: int = 50  # Early stopping


@dataclass
class PerformanceMetrics:
    """Performance metrics for learning evaluation."""

    # Basic metrics
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cognitive_load: float = 0.0
    response_time_ms: float = 0.0
    accuracy_score: float = 0.0

    # Flag-specific metrics
    flags_enabled: int = 0
    flags_disabled: int = 0
    cognitive_overrides: int = 0

    # Component metrics
    component_name: str = "unknown"
    operation_success: bool = True
    error_count: int = 0

    # Neural pathway metrics
    neural_pathway: Optional[NeuralPathway] = None
    brain_region: Optional[BrainRegion] = None
    pathway_efficiency: float = 0.0

    # Composite scores
    user_satisfaction: float = 0.0
    system_efficiency: float = 0.0
    cognitive_efficiency: float = 0.0


@dataclass
class LearningState:
    """Current state of the adaptive learning system."""

    # Learning progress
    iteration: int = 0
    convergence_score: float = 0.0
    best_performance: float = 0.0

    # Parameter evolution
    current_thresholds: Dict[str, float] = field(default_factory=dict)
    parameter_history: List[Dict[str, float]] = field(default_factory=list)
    performance_history: List[float] = field(default_factory=list)

    # Neural-inspired state
    synaptic_weights: Dict[str, float] = field(default_factory=dict)
    neural_activation: Dict[str, float] = field(default_factory=dict)
    plasticity_levels: Dict[str, float] = field(default_factory=dict)

    # Experience replay buffer
    experience_buffer: List[PerformanceMetrics] = field(default_factory=list)

    # Convergence tracking
    stable_iterations: int = 0
    last_improvement: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AdaptiveLearningEngine:
    """
    Brain-inspired adaptive learning engine for feature flag optimization.

    Provides neural network-inspired learning including:
    - Hebbian learning for correlation strengthening
    - Reinforcement learning for reward-based optimization
    - Neural plasticity for adaptive threshold adjustment
    - Genetic algorithms for parameter evolution
    - Experience replay for efficient learning
    """

    def __init__(self, cognitive_manager: CognitiveFlagManager):
        self.cognitive_manager = cognitive_manager
        self.learning_params = LearningParameters()
        self.learning_state = LearningState()

        # Learning configuration
        self.algorithm = LearningAlgorithm.NEURAL_PLASTICITY
        self.optimization_target = OptimizationTarget.COGNITIVE_EFFICIENCY

        # Component-specific learning states
        self.component_states: Dict[str, LearningState] = {}

        # Statistics
        self.learning_stats = {
            "learning_iterations": 0,
            "parameters_adapted": 0,
            "performance_improvements": 0,
            "convergence_achieved": 0,
            "exploration_decisions": 0,
            "exploitation_decisions": 0,
        }

    async def record_performance(self, metrics: PerformanceMetrics) -> None:
        """Record performance metrics for learning."""

        # Check if learning is enabled
        learning_flags = await self._get_learning_flags(metrics.cognitive_load)

        if not learning_flags.get("adaptive_learning_enabled", False):
            return

        # Add to experience buffer
        self.learning_state.experience_buffer.append(metrics)

        # Maintain buffer size
        if (
            len(self.learning_state.experience_buffer)
            > self.learning_params.memory_size
        ):
            self.learning_state.experience_buffer.pop(0)

        # Update component-specific state
        component = metrics.component_name
        if component not in self.component_states:
            self.component_states[component] = LearningState()

        self.component_states[component].experience_buffer.append(metrics)

        # Trigger learning if conditions are met
        if learning_flags.get("real_time_learning", False):
            await self._trigger_learning_update(metrics)

    async def optimize_cognitive_thresholds(
        self,
        component_name: Optional[str] = None,
        target: Optional[OptimizationTarget] = None,
    ) -> Dict[str, Any]:
        """Optimize cognitive load thresholds using adaptive learning."""

        target = target or self.optimization_target

        if component_name:
            # Optimize specific component
            if component_name not in self.component_states:
                return {
                    "status": "no_data",
                    "message": f"No learning data available for component: {component_name}",
                }

            return await self._optimize_component_thresholds(component_name, target)
        else:
            # Optimize all components
            results = {}
            for comp_name in self.component_states.keys():
                results[comp_name] = await self._optimize_component_thresholds(
                    comp_name, target
                )

            return {
                "status": "optimized",
                "component_results": results,
                "global_optimization": await self._optimize_global_thresholds(target),
            }

    async def apply_hebbian_learning(
        self, neural_pathway: NeuralPathway, performance_improvement: float
    ) -> None:
        """Apply Hebbian learning to strengthen successful neural pathways."""

        pathway_key = f"pathway_{neural_pathway.value}"

        # Initialize synaptic weight if not exists
        if pathway_key not in self.learning_state.synaptic_weights:
            self.learning_state.synaptic_weights[pathway_key] = 0.5

        # Hebbian rule: strengthen connections for successful activations
        current_weight = self.learning_state.synaptic_weights[pathway_key]

        # Calculate weight change based on performance improvement
        weight_change = self.learning_params.learning_rate * performance_improvement

        # Apply decay to prevent unlimited growth
        new_weight = current_weight + weight_change
        new_weight *= self.learning_params.decay_rate

        # Clamp weight to valid range
        self.learning_state.synaptic_weights[pathway_key] = max(
            0.0, min(1.0, new_weight)
        )

        # Update neural activation
        self.learning_state.neural_activation[pathway_key] = new_weight

        # Update plasticity level
        plasticity_change = abs(weight_change) * 0.1
        current_plasticity = self.learning_state.plasticity_levels.get(pathway_key, 0.5)
        self.learning_state.plasticity_levels[pathway_key] = min(
            1.0, current_plasticity + plasticity_change
        )

    async def apply_reinforcement_learning(
        self, action: str, reward: float, state: Dict[str, float]
    ) -> Dict[str, Any]:
        """Apply reinforcement learning to optimize flag decisions."""

        # Q-learning inspired update
        action_key = f"action_{action}"

        # Initialize Q-value if not exists
        if action_key not in self.learning_state.neural_activation:
            self.learning_state.neural_activation[action_key] = 0.0

        current_q = self.learning_state.neural_activation[action_key]

        # Estimate future Q-value (simplified)
        future_q = (
            max(self.learning_state.neural_activation.values())
            if self.learning_state.neural_activation
            else 0.0
        )

        # Q-learning update
        td_error = reward + self.learning_params.decay_rate * future_q - current_q
        new_q = current_q + self.learning_params.learning_rate * td_error

        self.learning_state.neural_activation[action_key] = new_q

        # Update exploration rate
        self.learning_params.exploration_rate *= self.learning_params.exploration_decay
        self.learning_params.exploration_rate = max(
            self.learning_params.min_exploration_rate,
            self.learning_params.exploration_rate,
        )

        return {
            "action": action,
            "q_value": new_q,
            "td_error": td_error,
            "exploration_rate": self.learning_params.exploration_rate,
        }

    async def adapt_cognitive_plasticity(
        self, cognitive_context: CognitiveFlagContext
    ) -> Dict[str, float]:
        """Adapt neural plasticity based on cognitive context."""

        # Calculate plasticity modulation based on cognitive load
        load_factor = (
            1.0 - cognitive_context.cognitive_load
        )  # Higher load = lower plasticity

        # Memory consolidation factor
        memory_factor = cognitive_context.hippocampus_activity * 0.5 + 0.5

        # Attention factor
        attention_factor = max(
            0.1, 1.0 - (cognitive_context.attention_queue_depth / 200.0)
        )

        # Overall plasticity modulation
        plasticity_modulation = load_factor * memory_factor * attention_factor

        # Update plasticity levels for all pathways
        adapted_plasticity = {}
        for (
            pathway_key,
            current_plasticity,
        ) in self.learning_state.plasticity_levels.items():
            # Apply modulation
            new_plasticity = current_plasticity * plasticity_modulation

            # Apply homeostatic scaling to prevent runaway plasticity
            new_plasticity = self._apply_homeostatic_scaling(
                new_plasticity, pathway_key
            )

            adapted_plasticity[pathway_key] = new_plasticity
            self.learning_state.plasticity_levels[pathway_key] = new_plasticity

        return adapted_plasticity

    async def evolve_parameters(
        self, population_size: int = 20, generations: int = 10
    ) -> Dict[str, Any]:
        """Use genetic algorithm to evolve optimal parameters."""

        # Check if genetic optimization is enabled
        learning_flags = await self._get_learning_flags(0.5)  # Medium load assumption

        if not learning_flags.get("genetic_optimization", False):
            return {
                "status": "disabled",
                "message": "Genetic optimization disabled due to cognitive load",
            }

        # Create initial population
        population = self._create_parameter_population(population_size)

        best_fitness = 0.0
        best_parameters = None

        for generation in range(generations):
            # Evaluate fitness for each individual
            fitness_scores = []
            for individual in population:
                fitness = await self._evaluate_parameter_fitness(individual)
                fitness_scores.append(fitness)

                if fitness > best_fitness:
                    best_fitness = fitness
                    best_parameters = individual.copy()

            # Selection and reproduction
            population = self._evolve_population(population, fitness_scores)

        # Apply best parameters
        if best_parameters:
            await self._apply_evolved_parameters(best_parameters)

        return {
            "status": "completed",
            "generations": generations,
            "best_fitness": best_fitness,
            "best_parameters": best_parameters,
            "final_population_size": len(population),
        }

    async def get_learning_insights(
        self, component_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get insights from adaptive learning."""

        if component_name and component_name in self.component_states:
            # Component-specific insights
            state = self.component_states[component_name]
            insights = await self._analyze_component_learning(component_name, state)
        else:
            # Global insights
            insights = await self._analyze_global_learning()

        return insights

    async def _get_learning_flags(self, cognitive_load: float) -> Dict[str, bool]:
        """Get adaptive learning flags based on cognitive load."""

        return {
            "adaptive_learning_enabled": cognitive_load
            < 0.8,  # Disable under high load
            "real_time_learning": cognitive_load
            < 0.6,  # Real-time only under medium load
            "genetic_optimization": cognitive_load < 0.4,  # Genetic only under low load
            "neural_plasticity": cognitive_load
            < 0.7,  # Plasticity under medium-low load
            "experience_replay": cognitive_load < 0.5,  # Replay under low load
        }

    async def _trigger_learning_update(self, metrics: PerformanceMetrics) -> None:
        """Trigger learning update based on new performance metrics."""

        # Calculate performance score
        performance_score = self._calculate_performance_score(metrics)

        # Update performance history
        self.learning_state.performance_history.append(performance_score)

        # Check for improvement
        if performance_score > self.learning_state.best_performance:
            self.learning_state.best_performance = performance_score
            self.learning_state.last_improvement = datetime.now(timezone.utc)
            self.learning_stats["performance_improvements"] += 1

        # Apply learning algorithms
        if metrics.neural_pathway:
            performance_improvement = performance_score - 0.5  # Baseline of 0.5
            await self.apply_hebbian_learning(
                metrics.neural_pathway, performance_improvement
            )

        # Apply reinforcement learning for flag decisions
        action = f"cognitive_load_{metrics.cognitive_load:.1f}"
        reward = performance_score
        state = {"cognitive_load": metrics.cognitive_load}

        await self.apply_reinforcement_learning(action, reward, state)

        self.learning_stats["learning_iterations"] += 1

    def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        """Calculate overall performance score from metrics."""

        if self.optimization_target == OptimizationTarget.PERFORMANCE:
            # Focus on speed and efficiency
            speed_score = max(0.0, 1.0 - (metrics.response_time_ms / 1000.0))
            efficiency_score = metrics.system_efficiency
            return speed_score * 0.6 + efficiency_score * 0.4

        elif self.optimization_target == OptimizationTarget.ACCURACY:
            # Focus on correctness
            return metrics.accuracy_score

        elif self.optimization_target == OptimizationTarget.COGNITIVE_EFFICIENCY:
            # Focus on cognitive load optimization
            load_efficiency = 1.0 - metrics.cognitive_load
            cognitive_score = metrics.cognitive_efficiency
            return load_efficiency * 0.4 + cognitive_score * 0.6

        elif self.optimization_target == OptimizationTarget.USER_EXPERIENCE:
            # Focus on user satisfaction
            return metrics.user_satisfaction

        else:  # BALANCED
            # Balance all factors
            speed_score = max(0.0, 1.0 - (metrics.response_time_ms / 1000.0))
            accuracy_score = metrics.accuracy_score
            cognitive_score = 1.0 - metrics.cognitive_load
            user_score = metrics.user_satisfaction

            return (speed_score + accuracy_score + cognitive_score + user_score) / 4.0

    async def _optimize_component_thresholds(
        self, component_name: str, target: OptimizationTarget
    ) -> Dict[str, Any]:
        """Optimize thresholds for a specific component."""

        state = self.component_states[component_name]

        if len(state.experience_buffer) < 10:
            return {
                "status": "insufficient_data",
                "message": f"Need more performance data for {component_name}",
            }

        # Analyze performance patterns
        performance_analysis = self._analyze_performance_patterns(
            state.experience_buffer
        )

        # Generate threshold recommendations
        recommendations = await self._generate_threshold_recommendations(
            component_name, performance_analysis, target
        )

        # Apply recommendations if confident
        if recommendations["confidence"] > 0.7:
            await self._apply_threshold_changes(
                component_name, recommendations["thresholds"]
            )
            status = "optimized"
        else:
            status = "analyzed"

        return {
            "status": status,
            "component": component_name,
            "analysis": performance_analysis,
            "recommendations": recommendations,
            "current_thresholds": state.current_thresholds.copy(),
        }

    async def _optimize_global_thresholds(
        self, target: OptimizationTarget
    ) -> Dict[str, Any]:
        """Optimize global cognitive thresholds."""

        # Aggregate performance data from all components
        all_metrics = []
        for state in self.component_states.values():
            all_metrics.extend(state.experience_buffer)

        if len(all_metrics) < 50:
            return {
                "status": "insufficient_global_data",
                "message": "Need more global performance data",
            }

        # Analyze global patterns
        global_analysis = self._analyze_performance_patterns(all_metrics)

        # Generate global recommendations
        global_recommendations = await self._generate_global_recommendations(
            global_analysis, target
        )

        return {
            "status": "analyzed",
            "global_analysis": global_analysis,
            "recommendations": global_recommendations,
        }

    def _apply_homeostatic_scaling(self, plasticity: float, pathway_key: str) -> float:
        """Apply homeostatic scaling to maintain stable plasticity."""

        # Target plasticity level
        target_plasticity = 0.5

        # Calculate deviation from target
        deviation = abs(plasticity - target_plasticity)

        # Apply gentle correction towards target
        correction_factor = 0.1
        if plasticity > target_plasticity:
            corrected_plasticity = plasticity - (deviation * correction_factor)
        else:
            corrected_plasticity = plasticity + (deviation * correction_factor)

        return max(0.0, min(1.0, corrected_plasticity))

    def _create_parameter_population(
        self, population_size: int
    ) -> List[Dict[str, float]]:
        """Create initial population for genetic algorithm."""

        population = []

        for _ in range(population_size):
            individual = {
                "cognitive_load_threshold": 0.5
                + (0.4 * (2 * math.sin(len(population)) - 1)),  # 0.1 to 0.9
                "learning_rate": 0.001
                + (0.099 * math.cos(len(population))),  # 0.001 to 0.1
                "exploration_rate": 0.01
                + (0.39 * abs(math.sin(len(population) * 2))),  # 0.01 to 0.4
                "plasticity_modulation": 0.3
                + (0.6 * abs(math.cos(len(population) * 1.5))),  # 0.3 to 0.9
            }
            population.append(individual)

        return population

    async def _evaluate_parameter_fitness(self, parameters: Dict[str, float]) -> float:
        """Evaluate fitness of parameter set."""

        # Simulate performance with these parameters
        simulated_metrics = self._simulate_performance_with_parameters(parameters)

        # Calculate fitness based on optimization target
        fitness = sum(
            self._calculate_performance_score(metrics) for metrics in simulated_metrics
        )
        fitness /= len(simulated_metrics) if simulated_metrics else 1.0

        return fitness

    def _evolve_population(
        self, population: List[Dict[str, float]], fitness_scores: List[float]
    ) -> List[Dict[str, float]]:
        """Evolve population using selection, crossover, and mutation."""

        # Selection: tournament selection
        selected = []
        tournament_size = 3

        for _ in range(len(population)):
            tournament_indices = [i for i in range(len(population))][:tournament_size]
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            winner_index = tournament_indices[
                tournament_fitness.index(max(tournament_fitness))
            ]
            selected.append(population[winner_index].copy())

        # Crossover and mutation
        new_population = []
        for i in range(0, len(selected), 2):
            parent1 = selected[i]
            parent2 = selected[i + 1] if i + 1 < len(selected) else selected[0]

            # Crossover
            child1, child2 = self._crossover(parent1, parent2)

            # Mutation
            child1 = self._mutate(child1)
            child2 = self._mutate(child2)

            new_population.extend([child1, child2])

        return new_population[: len(population)]

    def _crossover(
        self, parent1: Dict[str, float], parent2: Dict[str, float]
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        """Perform crossover between two parents."""

        child1 = {}
        child2 = {}

        for key in parent1.keys():
            if hash(key) % 2 == 0:  # Simple deterministic crossover
                child1[key] = parent1[key]
                child2[key] = parent2[key]
            else:
                child1[key] = parent2[key]
                child2[key] = parent1[key]

        return child1, child2

    def _mutate(self, individual: Dict[str, float]) -> Dict[str, float]:
        """Mutate an individual with small random changes."""

        mutation_rate = 0.1
        mutation_strength = 0.05

        mutated = individual.copy()

        for key, value in mutated.items():
            if (
                hash(key + str(value)) % 100 < mutation_rate * 100
            ):  # Deterministic mutation
                # Add small random change (simulated with hash)
                change = (
                    (hash(key + str(value)) % 200 - 100) / 1000.0 * mutation_strength
                )
                mutated[key] = max(0.0, min(1.0, value + change))

        return mutated

    def _simulate_performance_with_parameters(
        self, parameters: Dict[str, float]
    ) -> List[PerformanceMetrics]:
        """Simulate performance with given parameters."""

        # Simple simulation based on recent experience
        simulated_metrics = []

        if self.learning_state.experience_buffer:
            # Use recent metrics as baseline
            baseline_metrics = self.learning_state.experience_buffer[-10:]

            for baseline in baseline_metrics:
                # Simulate how parameters would affect performance
                simulated = PerformanceMetrics(
                    cognitive_load=baseline.cognitive_load,
                    response_time_ms=baseline.response_time_ms
                    * (2.0 - parameters["cognitive_load_threshold"]),
                    accuracy_score=baseline.accuracy_score
                    * (0.5 + parameters["plasticity_modulation"] * 0.5),
                    component_name=baseline.component_name,
                    operation_success=baseline.operation_success,
                    neural_pathway=baseline.neural_pathway,
                    brain_region=baseline.brain_region,
                    pathway_efficiency=baseline.pathway_efficiency
                    * parameters["plasticity_modulation"],
                    system_efficiency=baseline.system_efficiency
                    * (0.5 + parameters["cognitive_load_threshold"] * 0.5),
                    cognitive_efficiency=baseline.cognitive_efficiency
                    * parameters["plasticity_modulation"],
                )
                simulated_metrics.append(simulated)

        return simulated_metrics

    async def _apply_evolved_parameters(self, parameters: Dict[str, float]) -> None:
        """Apply evolved parameters to the learning system."""

        # Update learning parameters
        self.learning_params.learning_rate = parameters["learning_rate"]
        self.learning_params.exploration_rate = parameters["exploration_rate"]

        # Update thresholds in cognitive manager (simplified)
        # In real implementation, this would update the actual flag thresholds
        self.learning_state.current_thresholds.update(parameters)

        self.learning_stats["parameters_adapted"] += len(parameters)

    def _analyze_performance_patterns(
        self, metrics_list: List[PerformanceMetrics]
    ) -> Dict[str, Any]:
        """Analyze performance patterns in metrics."""

        if not metrics_list:
            return {"status": "no_data"}

        # Calculate basic statistics
        cognitive_loads = [m.cognitive_load for m in metrics_list]
        response_times = [m.response_time_ms for m in metrics_list]
        accuracy_scores = [m.accuracy_score for m in metrics_list]

        return {
            "sample_size": len(metrics_list),
            "cognitive_load": {
                "avg": sum(cognitive_loads) / len(cognitive_loads),
                "min": min(cognitive_loads),
                "max": max(cognitive_loads),
            },
            "response_time": {
                "avg": sum(response_times) / len(response_times),
                "min": min(response_times),
                "max": max(response_times),
            },
            "accuracy": {
                "avg": sum(accuracy_scores) / len(accuracy_scores),
                "min": min(accuracy_scores),
                "max": max(accuracy_scores),
            },
            "success_rate": sum(1 for m in metrics_list if m.operation_success)
            / len(metrics_list),
        }

    async def _generate_threshold_recommendations(
        self, component_name: str, analysis: Dict[str, Any], target: OptimizationTarget
    ) -> Dict[str, Any]:
        """Generate threshold recommendations based on analysis."""

        recommendations = {"thresholds": {}, "confidence": 0.0, "reasoning": []}

        if analysis.get("status") == "no_data":
            return recommendations

        # Analyze current performance
        avg_load = analysis["cognitive_load"]["avg"]
        avg_response = analysis["response_time"]["avg"]
        success_rate = analysis["success_rate"]

        # Generate recommendations based on target
        if target == OptimizationTarget.PERFORMANCE:
            if avg_response > 500:  # Slow response
                recommendations["thresholds"]["cognitive_load_threshold"] = min(
                    0.9, avg_load + 0.1
                )
                recommendations["reasoning"].append(
                    "Increase cognitive load threshold to enable more features"
                )

            recommendations["confidence"] = 0.7 if success_rate > 0.8 else 0.5

        elif target == OptimizationTarget.COGNITIVE_EFFICIENCY:
            if avg_load > 0.7:  # High cognitive load
                recommendations["thresholds"]["cognitive_load_threshold"] = max(
                    0.3, avg_load - 0.2
                )
                recommendations["reasoning"].append(
                    "Decrease cognitive load threshold to reduce load"
                )

            recommendations["confidence"] = 0.8 if analysis["sample_size"] > 20 else 0.6

        return recommendations

    async def _generate_global_recommendations(
        self, analysis: Dict[str, Any], target: OptimizationTarget
    ) -> Dict[str, Any]:
        """Generate global optimization recommendations."""

        return {
            "global_threshold_adjustments": {
                "cognitive_load_baseline": 0.5,
                "performance_threshold": 0.8,
                "accuracy_threshold": 0.9,
            },
            "optimization_strategy": target.value,
            "confidence": 0.7,
            "reasoning": [
                "Global analysis shows balanced performance across components",
                "Recommend gradual threshold adjustments",
                "Monitor for 24 hours before further optimization",
            ],
        }

    async def _apply_threshold_changes(
        self, component_name: str, thresholds: Dict[str, float]
    ) -> None:
        """Apply threshold changes to component."""

        # Update component state
        if component_name not in self.component_states:
            self.component_states[component_name] = LearningState()

        self.component_states[component_name].current_thresholds.update(thresholds)

        # Record parameter change
        self.component_states[component_name].parameter_history.append(
            thresholds.copy()
        )

        self.learning_stats["parameters_adapted"] += len(thresholds)

    async def _analyze_component_learning(
        self, component_name: str, state: LearningState
    ) -> Dict[str, Any]:
        """Analyze learning progress for a component."""

        return {
            "component": component_name,
            "learning_iterations": state.iteration,
            "best_performance": state.best_performance,
            "current_thresholds": state.current_thresholds,
            "synaptic_weights": state.synaptic_weights,
            "plasticity_levels": state.plasticity_levels,
            "experience_buffer_size": len(state.experience_buffer),
            "parameter_changes": len(state.parameter_history),
            "convergence_score": state.convergence_score,
        }

    async def _analyze_global_learning(self) -> Dict[str, Any]:
        """Analyze global learning progress."""

        return {
            "global_learning_stats": self.learning_stats,
            "learning_parameters": {
                "learning_rate": self.learning_params.learning_rate,
                "exploration_rate": self.learning_params.exploration_rate,
                "decay_rate": self.learning_params.decay_rate,
            },
            "optimization_target": self.optimization_target.value,
            "learning_algorithm": self.algorithm.value,
            "component_count": len(self.component_states),
            "total_experience": sum(
                len(s.experience_buffer) for s in self.component_states.values()
            ),
            "global_synaptic_weights": self.learning_state.synaptic_weights,
            "global_plasticity": self.learning_state.plasticity_levels,
        }

    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics."""

        return {
            **self.learning_stats,
            "learning_state": {
                "iteration": self.learning_state.iteration,
                "best_performance": self.learning_state.best_performance,
                "convergence_score": self.learning_state.convergence_score,
                "stable_iterations": self.learning_state.stable_iterations,
            },
            "component_states": len(self.component_states),
            "total_experience": len(self.learning_state.experience_buffer),
            "synaptic_connections": len(self.learning_state.synaptic_weights),
            "plasticity_connections": len(self.learning_state.plasticity_levels),
        }

    def reset_learning_state(self, component_name: Optional[str] = None) -> None:
        """Reset learning state for component or globally."""

        if component_name:
            if component_name in self.component_states:
                self.component_states[component_name] = LearningState()
        else:
            self.learning_state = LearningState()
            self.component_states.clear()
            self.learning_stats = {
                "learning_iterations": 0,
                "parameters_adapted": 0,
                "performance_improvements": 0,
                "convergence_achieved": 0,
                "exploration_decisions": 0,
                "exploitation_decisions": 0,
            }
