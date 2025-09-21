#!/usr/bin/env python3
"""
Bootstrap MemoryOS Observability
================================

This script helps you set up the observability layer for MemoryOS development.
It can set up local development environment or Kubernetes deployments.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def check_prerequisites():
    """Check if required tools are installed"""
    tools = {
        "docker": "Docker is required for local development",
        "kubectl": "kubectl is required for Kubernetes deployment",
        "kustomize": "kustomize is required for Kubernetes deployment (optional)",
    }

    missing = []
    for tool, description in tools.items():
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
            print(f"✅ {tool} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append((tool, description))
            print(f"❌ {tool} is not installed - {description}")

    return missing


def setup_local():
    """Set up local development environment with Docker Compose"""
    print("🚀 Setting up local observability stack...")

    os.chdir(Path(__file__).parent.parent / "deployments" / "local")

    try:
        # Start the stack
        subprocess.run(["docker-compose", "up", "-d"], check=True)

        print("\n✅ Local observability stack is running!")
        print("\n📊 Access points:")
        print("  • MemoryOS API: http://localhost:8080")
        print("  • Metrics: http://localhost:8081/v1/metrics")
        print("  • Grafana: http://localhost:3000 (admin/admin)")
        print("  • Prometheus: http://localhost:9090")
        print("  • Jaeger: http://localhost:16686")

        print("\n🔍 To check status:")
        print("  docker-compose ps")
        print("\n🛑 To stop:")
        print("  docker-compose down")

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start local stack: {e}")
        return False

    return True


def setup_kubernetes():
    """Set up Kubernetes deployment"""
    print("☸️  Setting up Kubernetes observability...")

    base_dir = Path(__file__).parent.parent / "deployments" / "kubernetes"

    try:
        # Create namespaces
        subprocess.run(
            ["kubectl", "create", "namespace", "memoryos"], capture_output=True
        )
        subprocess.run(
            ["kubectl", "create", "namespace", "monitoring"], capture_output=True
        )

        # Apply base configuration
        os.chdir(base_dir / "base")
        subprocess.run(["kubectl", "apply", "-k", "."], check=True)

        # Apply monitoring configurations
        monitoring_dir = base_dir.parent / "monitoring"
        if (monitoring_dir / "kubernetes").exists():
            os.chdir(monitoring_dir / "kubernetes")
            subprocess.run(["kubectl", "apply", "-f", "."], check=True)

        print("\n✅ Kubernetes observability deployed!")
        print("\n🔍 Check deployment status:")
        print("  kubectl get pods -n memoryos")
        print("  kubectl get pods -n monitoring")

        print("\n📊 Port forward to access services:")
        print("  kubectl port-forward -n memoryos svc/memoryos 8080:8080")
        print("  kubectl port-forward -n monitoring svc/grafana 3000:3000")

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to deploy to Kubernetes: {e}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Bootstrap MemoryOS Observability")
    parser.add_argument(
        "mode", choices=["local", "k8s", "check"], help="Deployment mode"
    )
    parser.add_argument(
        "--skip-check", action="store_true", help="Skip prerequisite checks"
    )

    args = parser.parse_args()

    if args.mode == "check" or not args.skip_check:
        print("🔍 Checking prerequisites...")
        missing = check_prerequisites()

        if args.mode == "check":
            if missing:
                print(f"\n❌ Missing {len(missing)} required tools")
                for tool, desc in missing:
                    print(f"  • {tool}: {desc}")
                return 1
            else:
                print("\n✅ All prerequisites are installed!")
                return 0

        if missing and args.mode != "check":
            print(f"\n⚠️  Warning: {len(missing)} tools are missing")
            for tool, desc in missing:
                print(f"  • {tool}: {desc}")

            if input("\nContinue anyway? (y/N): ").lower() != "y":
                return 1

    if args.mode == "local":
        success = setup_local()
    elif args.mode == "k8s":
        success = setup_kubernetes()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
