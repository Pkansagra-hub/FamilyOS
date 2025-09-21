#!/usr/bin/env python3
"""
Simple Local Development Setup (No Docker Required)
==================================================

This sets up basic observability for MemoryOS development without Docker.
Perfect for getting started quickly while Docker is being installed.
"""

import subprocess
import sys
import os
from pathlib import Path
import time
import webbrowser
from threading import Thread

def install_prometheus_client():
    """Install prometheus_client if not available"""
    try:
        import prometheus_client
        print("✅ prometheus_client is already installed")
        return True
    except ImportError:
        print("📦 Installing prometheus_client...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'prometheus_client'],
                         check=True)
            print("✅ prometheus_client installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install prometheus_client")
            return False

def create_simple_metrics_server():
    """Create a simple metrics server for development"""
    metrics_server_code = '''
import time
import random
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Define some sample metrics for MemoryOS
REQUEST_COUNT = Counter('memoryos_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('memoryos_request_duration_seconds', 'Request duration')
MEMORY_USAGE = Gauge('memoryos_memory_usage_bytes', 'Memory usage')
PIPELINE_LATENCY = Histogram('memoryos_pipeline_latency_ms', 'Pipeline latency', ['pipeline'])

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            # Simulate some metrics
            REQUEST_COUNT.labels(method='GET', endpoint='/metrics').inc()
            MEMORY_USAGE.set(random.uniform(100000000, 500000000))  # 100-500MB

            # Simulate pipeline metrics
            for pipeline in ['P01', 'P02', 'P03', 'P04']:
                PIPELINE_LATENCY.labels(pipeline=pipeline).observe(random.uniform(10, 100))

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(generate_latest())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging
        pass

def run_metrics_server():
    server = HTTPServer(('localhost', 8081), MetricsHandler)
    print("📊 Metrics server running on http://localhost:8081/metrics")
    server.serve_forever()

if __name__ == '__main__':
    # Start metrics server in background
    metrics_thread = threading.Thread(target=run_metrics_server, daemon=True)
    metrics_thread.start()

    print("🚀 Simple MemoryOS metrics demo running!")
    print("📊 Metrics: http://localhost:8081/metrics")
    print("🔍 Try opening the URL in your browser")
    print("⏹️  Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\\n✅ Stopped metrics server")
'''

    with open('simple_metrics_server.py', 'w') as f:
        f.write(metrics_server_code)

    return 'simple_metrics_server.py'

def setup_simple_local():
    """Set up simple local development without Docker"""
    print("🔧 Setting up simple local development environment...")

    # Install dependencies
    if not install_prometheus_client():
        return False

    # Create simple metrics server
    metrics_file = create_simple_metrics_server()

    print(f"\n✅ Created {metrics_file}")
    print("\n🚀 To start the demo:")
    print(f"  python {metrics_file}")

    # Ask if they want to start it now
    if input("\n▶️  Start the metrics demo now? (y/N): ").lower() == 'y':
        print("\n🚀 Starting metrics demo...")
        try:
            subprocess.run([sys.executable, metrics_file])
        except KeyboardInterrupt:
            print("\n✅ Demo stopped")

    return True

def show_next_steps():
    """Show what to do next"""
    print("\n📋 Next Steps:")
    print("\n1️⃣  **Install Docker Desktop**:")
    print("   https://www.docker.com/products/docker-desktop/")

    print("\n2️⃣  **Once Docker is installed, run**:")
    print("   cd deployments")
    print("   python bootstrap.py local")

    print("\n3️⃣  **For now, you can use the simple setup**:")
    print("   python simple_metrics_server.py")
    print("   # Then visit http://localhost:8081/metrics")

    print("\n4️⃣  **Optional: Install kubectl for Kubernetes**:")
    print("   # For Windows with Chocolatey:")
    print("   choco install kubernetes-cli")
    print("   # Or download from: https://kubernetes.io/docs/tasks/tools/")

def main():
    print("🛠️  MemoryOS Simple Local Setup")
    print("=" * 40)

    # Check current directory
    if not Path('deployments').exists():
        print("❌ Run this from the MemoryOS root directory")
        print("   cd back to: G:\\memoryOS")
        return 1

    os.chdir('deployments/local')

    success = setup_simple_local()

    if success:
        show_next_steps()
        return 0
    else:
        print("❌ Setup failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
'''
