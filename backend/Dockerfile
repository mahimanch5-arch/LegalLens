# Multi-stage build for LegalLens Backend
# Stage 1: Builder stage - installs dependencies with uv
# Stage 2: Runtime stage - runs FastAPI application

# === STAGE 1: BUILDER ===
# Using Python 3.13 slim-bookworm for building
# Slim variant includes just enough to run Python apps (~150MB)
FROM python:3.13-slim-bookworm AS builder

LABEL maintainer="LegalLens Team"
LABEL stage=builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building (not runtime)
# These are removed in final image, only needed to install Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv - fast Python package manager (50x faster than pip)
# uv is standalone, works like pip but with better performance
RUN pip install --no-cache-dir uv==0.4.0

# Copy dependency files first for Docker layer caching
# If pyproject.toml and uv.lock don't change, this layer is reused
COPY pyproject.toml uv.lock ./

# Install Python dependencies with uv
# --frozen ensures exact versions from uv.lock (reproducible builds)
# --no-dev excludes dev dependencies (testing, linting, etc.)
RUN uv sync --frozen --no-dev

# Copy source code after dependencies are installed
# This way, code changes don't invalidate the dependency layer
COPY . .


# === STAGE 2: RUNTIME ===
# Using Python 3.13 slim-bookworm (lightweight base image)
# Slim is sufficient - includes Python runtime but not build tools
FROM python:3.13-slim-bookworm

LABEL maintainer="LegalLens Team"
LABEL stage=runtime

WORKDIR /app

# Install only runtime dependencies (not build tools from builder)
# These are minimal: libraries needed by the app at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    libffi8 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for running the application (security best practice)
# Prevents container from running as root if compromised
RUN useradd --create-home --shell /bin/bash appuser

# Copy Python environment from builder stage
# Contains all installed packages in isolated virtual environment
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code from builder stage
COPY --from=builder --chown=appuser:appuser /app /app

# Set PATH to use virtual environment's Python
# This ensures we use the right Python binary and installed packages
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Create directory for application data (SQLite database, etc.)
# Used by the app for storing state
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Switch to non-root user for running the app
USER appuser

# Expose port 8000 (Uvicorn default)
# FastAPI runs on this port inside container
EXPOSE 8000

# Healthcheck: HTTP GET to /api/docs should return 200
# Used by Docker, Kubernetes liveness/readiness probes
# Interval 30s, timeout 3s, start period 10s (app needs time to initialize DB), retries 3
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/api/docs > /dev/null || exit 1

# Run Uvicorn ASGI server
# Serves FastAPI application on 0.0.0.0:8000
# Workers: single worker for stateless design (scale with containers, not processes)
# Host 0.0.0.0: listen on all interfaces (required in containers)
# Access log: enabled for monitoring in production
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log"]
