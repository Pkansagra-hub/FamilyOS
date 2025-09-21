#!/usr/bin/env python3
"""
Feature Flag CLI Tool
=====================

Command-line interface for managing MemoryOS feature flags.
Provides commands for listing, toggling, and evaluating flags.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core import Environment, FeatureFlagManager


class FeatureFlagCLI:
    """Command-line interface for feature flag management."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.manager: Optional[FeatureFlagManager] = None

    async def initialize(self, environment: Environment = Environment.DEVELOPMENT):
        """Initialize the CLI with feature flag manager."""
        self.manager = FeatureFlagManager(
            config_path=self.config_path,
            environment=environment,
            enable_hot_reload=False,
        )
        await self.manager.initialize()

    async def list_flags(
        self, category: Optional[str] = None, show_details: bool = False
    ):
        """List all available flags or flags in a specific category."""
        if not self.manager:
            print("Error: Manager not initialized")
            return

        if category:
            flags = self.manager.get_flags_by_category_definition(category)
            print(f"\n=== Flags in category '{category}' ===")
        else:
            flags = self.manager.get_available_flags()
            print(f"\n=== All Available Flags ({len(flags)}) ===")

        if not flags:
            print("No flags found.")
            return

        for flag_name, flag in flags.items():
            status = "ENABLED" if flag.enabled else "DISABLED"
            cognitive = " [COGNITIVE]" if flag.is_cognitive_aware() else ""

            if show_details:
                print(f"\n{flag_name}: {status}{cognitive}")
                print(f"  Description: {flag.description}")
                print(f"  Category: {flag.category}")
                print(f"  Type: {flag.flag_type.value}")
                print(f"  Default: {flag.default_value}")

                if flag.is_cognitive_aware() and flag.cognitive_context:
                    ctx = flag.cognitive_context
                    print("  Cognitive Context:")
                    print(f"    Load Aware: {ctx.load_aware}")
                    print(f"    Load Threshold: {ctx.cognitive_load_threshold}")
                    if ctx.neural_pathway:
                        print(f"    Neural Pathway: {ctx.neural_pathway}")
                    if ctx.brain_region:
                        print(f"    Brain Region: {ctx.brain_region}")
                    print(f"    Performance Impact: {ctx.performance_impact}")
            else:
                print(f"  {flag_name}: {status}{cognitive} - {flag.description}")

    async def evaluate_flag(
        self,
        flag_name: str,
        cognitive_load: float = 0.0,
        working_memory_load: float = 0.0,
        attention_queue_depth: int = 0,
        neural_pathway: Optional[str] = None,
        brain_region: Optional[str] = None,
    ):
        """Evaluate a specific flag with given context."""
        if not self.manager:
            print("Error: Manager not initialized")
            return

        context = self.manager.create_context(
            cognitive_load=cognitive_load,
            working_memory_load=working_memory_load,
            attention_queue_depth=attention_queue_depth,
            neural_pathway=neural_pathway,
            brain_region=brain_region,
        )

        result = await self.manager.get_flag_details(flag_name, context)

        if not result:
            print(f"Flag '{flag_name}' not found")
            return

        print(f"\n=== Flag Evaluation: {flag_name} ===")
        print(f"Value: {result.value}")
        print(f"Rule Applied: {result.rule_applied}")
        print(f"Evaluation Time: {result.evaluation_time_ms:.2f}ms")
        print(f"Cache Hit: {result.cache_hit}")
        print(f"Cognitive Override: {result.cognitive_override}")
        if result.reason:
            print(f"Reason: {result.reason}")

    async def evaluate_category(
        self,
        category: str,
        cognitive_load: float = 0.0,
        working_memory_load: float = 0.0,
        attention_queue_depth: int = 0,
        neural_pathway: Optional[str] = None,
        brain_region: Optional[str] = None,
    ):
        """Evaluate all flags in a category."""
        if not self.manager:
            print("Error: Manager not initialized")
            return

        context = self.manager.create_context(
            cognitive_load=cognitive_load,
            working_memory_load=working_memory_load,
            attention_queue_depth=attention_queue_depth,
            neural_pathway=neural_pathway,
            brain_region=brain_region,
        )

        flags = await self.manager.get_flags_by_category(category, context)

        if not flags:
            print(f"No flags found in category '{category}'")
            return

        print(f"\n=== Category Evaluation: {category} ===")
        for flag_name, enabled in flags.items():
            status = "ENABLED" if enabled else "DISABLED"
            print(f"  {flag_name}: {status}")

    async def cognitive_simulation(self):
        """Run a cognitive load simulation showing flag behavior."""
        if not self.manager:
            print("Error: Manager not initialized")
            return

        print("\n=== Cognitive Load Simulation ===")
        print("Simulating different cognitive states...\n")

        # Get cognitive flags
        cognitive_flags = self.manager.get_cognitive_flag_definitions()
        if not cognitive_flags:
            print("No cognitive flags found.")
            return

        # Test different load scenarios
        scenarios = [
            {"name": "Low Load", "cognitive_load": 0.1, "working_memory_load": 0.2},
            {"name": "Medium Load", "cognitive_load": 0.5, "working_memory_load": 0.6},
            {"name": "High Load", "cognitive_load": 0.8, "working_memory_load": 0.9},
            {
                "name": "Critical Load",
                "cognitive_load": 0.95,
                "working_memory_load": 0.95,
            },
        ]

        for scenario in scenarios:
            print(f"--- {scenario['name']} Scenario ---")
            context = self.manager.create_context(
                cognitive_load=scenario["cognitive_load"],
                working_memory_load=scenario["working_memory_load"],
                attention_queue_depth=50 if scenario["cognitive_load"] > 0.7 else 10,
            )

            for flag_name in list(cognitive_flags.keys())[:5]:  # Show first 5 flags
                result = await self.manager.get_flag_details(flag_name, context)
                if result:
                    status = "ON" if result.value else "OFF"
                    print(f"  {flag_name}: {status} ({result.rule_applied})")
            print()

    async def show_stats(self):
        """Show performance statistics."""
        if not self.manager:
            print("Error: Manager not initialized")
            return

        stats = self.manager.get_performance_stats()

        print("\n=== Performance Statistics ===")
        print("Manager Stats:")
        for key, value in stats["manager"].items():
            print(f"  {key}: {value}")

        print("\nEvaluator Stats:")
        for key, value in stats["evaluator"].items():
            print(f"  {key}: {value}")

        print("\nConfig Stats:")
        for key, value in stats["config"].items():
            print(f"  {key}: {value}")

    async def validate_config(self):
        """Validate the current configuration."""
        if not self.manager:
            print("Error: Manager not initialized")
            return

        validation = await self.manager.validate_config()

        print("\n=== Configuration Validation ===")
        print(f"Valid: {validation['valid']}")
        print(f"Flags: {validation['flag_count']}")
        print(f"Categories: {len(validation['categories'])}")
        print(f"Cognitive Flags: {validation['cognitive_flags']}")

        if validation["errors"]:
            print(f"\nErrors ({len(validation['errors'])}):")
            for error in validation["errors"]:
                print(f"  ❌ {error}")

        if validation["warnings"]:
            print(f"\nWarnings ({len(validation['warnings'])}):")
            for warning in validation["warnings"]:
                print(f"  ⚠️  {warning}")

        if validation["valid"] and not validation["errors"]:
            print("\n✅ Configuration is valid!")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MemoryOS Feature Flag Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                           # List all flags
  %(prog)s list --category working_memory # List flags in category
  %(prog)s eval memory_l2_cache          # Evaluate specific flag
  %(prog)s eval memory_l2_cache --cognitive-load 0.8
  %(prog)s simulate                      # Run cognitive simulation
  %(prog)s stats                         # Show performance stats
  %(prog)s validate                      # Validate configuration
        """,
    )

    parser.add_argument("--config", type=Path, help="Path to configuration YAML file")
    parser.add_argument(
        "--environment",
        choices=["development", "testing", "production"],
        default="development",
        help="Environment to use for evaluation",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List available flags")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument(
        "--details", action="store_true", help="Show detailed information"
    )

    # Evaluate command
    eval_parser = subparsers.add_parser("eval", help="Evaluate a specific flag")
    eval_parser.add_argument("flag_name", help="Name of the flag to evaluate")
    eval_parser.add_argument(
        "--cognitive-load", type=float, default=0.0, help="Cognitive load (0.0-1.0)"
    )
    eval_parser.add_argument(
        "--working-memory-load",
        type=float,
        default=0.0,
        help="Working memory load (0.0-1.0)",
    )
    eval_parser.add_argument(
        "--attention-queue-depth", type=int, default=0, help="Attention queue depth"
    )
    eval_parser.add_argument("--neural-pathway", help="Neural pathway identifier")
    eval_parser.add_argument("--brain-region", help="Brain region identifier")

    # Category evaluation
    cat_parser = subparsers.add_parser(
        "category", help="Evaluate all flags in a category"
    )
    cat_parser.add_argument("category", help="Category name")
    cat_parser.add_argument(
        "--cognitive-load", type=float, default=0.0, help="Cognitive load (0.0-1.0)"
    )
    cat_parser.add_argument(
        "--working-memory-load",
        type=float,
        default=0.0,
        help="Working memory load (0.0-1.0)",
    )
    cat_parser.add_argument(
        "--attention-queue-depth", type=int, default=0, help="Attention queue depth"
    )
    cat_parser.add_argument("--neural-pathway", help="Neural pathway identifier")
    cat_parser.add_argument("--brain-region", help="Brain region identifier")

    # Other commands
    subparsers.add_parser("simulate", help="Run cognitive load simulation")
    subparsers.add_parser("stats", help="Show performance statistics")
    subparsers.add_parser("validate", help="Validate configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Map environment string to enum
    env_map = {
        "development": Environment.DEVELOPMENT,
        "testing": Environment.TESTING,
        "production": Environment.PRODUCTION,
    }
    environment = env_map[args.environment]

    # Initialize CLI
    cli = FeatureFlagCLI(args.config)
    try:
        await cli.initialize(environment)

        # Execute command
        if args.command == "list":
            await cli.list_flags(args.category, args.details)
        elif args.command == "eval":
            await cli.evaluate_flag(
                args.flag_name,
                args.cognitive_load,
                args.working_memory_load,
                args.attention_queue_depth,
                args.neural_pathway,
                args.brain_region,
            )
        elif args.command == "category":
            await cli.evaluate_category(
                args.category,
                args.cognitive_load,
                args.working_memory_load,
                args.attention_queue_depth,
                args.neural_pathway,
                args.brain_region,
            )
        elif args.command == "simulate":
            await cli.cognitive_simulation()
        elif args.command == "stats":
            await cli.show_stats()
        elif args.command == "validate":
            await cli.validate_config()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if cli.manager:
            await cli.manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
