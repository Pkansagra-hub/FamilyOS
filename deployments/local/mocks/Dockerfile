FROM python:3.11-slim

LABEL maintainer="MemoryOS Team"
LABEL description="Mock external services for MemoryOS development"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-mock.txt .
RUN pip install --no-cache-dir -r requirements-mock.txt

# Copy mock services
COPY mock_services.py .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

# Expose port
EXPOSE 8090

# Run the mock services
CMD ["python", "mock_services.py"]
