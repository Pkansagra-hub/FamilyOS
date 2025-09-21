#!/bin/bash
# MemoryOS Development Entrypoint Script
# =====================================
# Sub-issue #5.2: Hot-reload development workflow

set -e

echo "🚀 Starting MemoryOS Development Environment"
echo "============================================="

# Dependencies are already checked by init containers
echo "✅ Dependencies ready (checked by init containers)"

# Set up Python path
export PYTHONPATH="${PYTHONPATH}:/app"

# Set up environment
echo "🌍 Environment: ${ENVIRONMENT:-development}"
echo "📝 Log Level: ${LOG_LEVEL:-DEBUG}"

# Set up development environment
echo "🔧 Setting up development environment..."

# Create necessary directories
mkdir -p /tmp/prometheus_multiproc
mkdir -p /app/logs

# Set permissions
chmod -R 755 /tmp/prometheus_multiproc
chmod -R 755 /app/logs

# Initialize database if needed
if [ "${INITIALIZE_DB:-false}" = "true" ]; then
    echo "🗄️ Initializing database..."
    python -c "
import asyncio
from core.database import initialize_database

async def init():
    await initialize_database()
    print('✅ Database initialized')

asyncio.run(init())
" || echo "⚠️ Database initialization failed (might already exist)"
fi

# Create MinIO buckets if needed
if [ "${INITIALIZE_STORAGE:-false}" = "true" ]; then
    echo "🪣 Setting up MinIO buckets..."
    python -c "
import boto3
from botocore.client import Config

# Configure MinIO client
client = boto3.client(
    's3',
    endpoint_url=f'http://${MINIO_HOST:-minio}:${MINIO_PORT:-9000}',
    aws_access_key_id='${MINIO_ACCESS_KEY:-minioadmin}',
    aws_secret_access_key='${MINIO_SECRET_KEY:-minioadmin123}',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# Create bucket if it doesn't exist
bucket_name = '${MINIO_BUCKET:-memoryos-data}'
try:
    client.head_bucket(Bucket=bucket_name)
    print(f'✅ Bucket {bucket_name} already exists')
except:
    client.create_bucket(Bucket=bucket_name)
    print(f'✅ Bucket {bucket_name} created')
" || echo "⚠️ MinIO bucket setup failed"
fi

# Set up hot-reload file watcher if in development mode
if [ "${ENVIRONMENT:-local}" = "local" ] && [ "${ENABLE_HOT_RELOAD:-true}" = "true" ]; then
    echo "🔥 Enabling hot-reload development mode"

    # Set up file watcher for additional reload triggers
    python -c "
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import threading

class ReloadHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_reload = 0

    def on_modified(self, event):
        if event.is_directory:
            return

        # Only reload for Python files
        if not event.src_path.endswith('.py'):
            return

        # Debounce reloads
        now = time.time()
        if now - self.last_reload < 1:
            return

        self.last_reload = now
        print(f'🔄 File changed: {event.src_path}')

# Start file watcher in background
observer = Observer()
observer.schedule(ReloadHandler(), '/app', recursive=True)
observer.start()

def signal_handler(signum, frame):
    observer.stop()
    observer.join()
    sys.exit(0)

import signal
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print('📂 File watcher started for hot-reload')
" &
fi

# Enable debugging if requested
if [ "${ENABLE_DEBUG:-false}" = "true" ]; then
    echo "🐛 Debug mode enabled - debugpy listening on port 5678"
    export DEBUGPY_ARGS="--listen 0.0.0.0:5678 --wait-for-client"
fi

# Show environment info
echo "📋 Environment Configuration:"
echo "  - Environment: ${ENVIRONMENT:-local}"
echo "  - Log Level: ${LOG_LEVEL:-DEBUG}"
echo "  - Hot Reload: ${ENABLE_HOT_RELOAD:-true}"
echo "  - Debug Mode: ${ENABLE_DEBUG:-false}"
echo "  - Database: ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}"
echo "  - Redis: ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}"
echo "  - MinIO: ${MINIO_HOST:-minio}:${MINIO_PORT:-9000}"

echo ""
echo "🎉 Development environment ready!"
echo "📡 API will be available at: http://localhost:8000"
echo "📊 Metrics available at: http://localhost:8080"
echo "📚 API docs available at: http://localhost:8000/docs"
echo ""

# Execute the main command
exec "$@"
