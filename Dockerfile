# Multi-stage Dockerfile for MemoryOS
# Sub-issue #6.3: Set up staging deployment

ARG PYTHON_VERSION=3.11

# Stage 1: Base Python environment
FROM python:${PYTHON_VERSION}-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base as deps

# Install Poetry
RUN pip install poetry==1.6.1

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy dependency files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Stage 3: Production image
FROM base as production

# Create non-root user
RUN groupadd -r memoryos && useradd -r -g memoryos memoryos

# Set working directory
WORKDIR /app

# Copy virtual environment from deps stage
COPY --from=deps /app/.venv /app/.venv

# Make sure to use venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --chown=memoryos:memoryos . .

# Switch to non-root user
USER memoryos

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 4: Development image
FROM deps as development

# Install development dependencies
RUN poetry install --no-root

# Copy application code
COPY . .

# Set environment for development
ENV ENVIRONMENT=development

# Expose port
EXPOSE 8000

# Command for development (with hot reload)
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
