## LegalLens Backend - Docker Guide

**Production-ready Docker setup for FastAPI + Python + uv**

---

## 📋 Overview

- **Base Image (Builder):** `python:3.13-slim-bookworm` with uv
- **Base Image (Runtime):** `python:3.13-slim-bookworm` (lightweight)
- **Final Image Size:** ~200-250 MB
- **Port:** 8000 (Uvicorn ASGI server)
- **Runs As:** Non-root user (`appuser`)
- **Health Check:** HTTP GET to `/api/docs` endpoint
- **Package Manager:** uv (50x faster than pip)

---

## 🏗️ Architecture Decisions

### Multi-Stage Build (Why?)

```
Stage 1: python:3.13-slim-bookworm
  ├─ Install build tools (gcc, libssl-dev, etc.)
  ├─ Install uv package manager
  ├─ Install dependencies with uv sync --frozen
  └─ Copy source code

Stage 2: python:3.13-slim-bookworm
  ├─ Install ONLY runtime dependencies (no gcc, no build tools)
  ├─ Copy .venv from Stage 1
  ├─ Copy app code from Stage 1
  └─ Final size: ~200-250 MB
```

**Why two stages?**
- Build tools (gcc, etc.) add 500+ MB, never needed at runtime
- Final image only needs Python runtime + dependencies
- Reduces final image by 60% without sacrificing functionality

### Python 3.13 slim-bookworm (Why?)

| Option | Size | Contains |
|--------|------|----------|
| python:3.13 | 1+ GB | Everything |
| python:3.13-slim | 150 MB | Python + minimal libs |
| python:3.13-slim-bookworm | 150 MB | Python + libssl (needed for requests, cryptography) |

**Verdict:** slim-bookworm is the right balance: small but includes essential libs.

### uv Package Manager (Why?)

| Tool | Speed | Reproducibility | Lock File |
|------|-------|-----------------|-----------|
| pip | Slow | Variable | requirements.txt (manual) |
| Poetry | Moderate | Good | poetry.lock |
| uv | **50x faster** | **Excellent** | uv.lock (auto-generated) |

**Verdict:** uv is fastest, uses existing pyproject.toml/uv.lock, perfect for containers.

### Single Worker + Containers (Why?)

```
Traditional: 1 container with 4 workers (multiprocessing)
Modern:      4 containers with 1 worker each (kubernetes scales)
```

**Why?**
- Containers are ephemeral: scale by adding containers, not processes
- Kubernetes orchestrates multiple containers
- Simpler memory/CPU management per container
- Better isolation: one container crash doesn't take down 3 other workers

### Health Check (Why?)

```nginx
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s
    CMD curl http://localhost:8000/api/docs
```

**Why?**
- Docker uses it to detect dead containers
- Kubernetes uses it for liveness (restart) and readiness (traffic) probes
- `/api/docs` requires successful app startup and database init

---

## 🔨 Build the Image

### Command

```bash
# Build with tag legallens-backend:local
docker build \
  --tag legallens-backend:local \
  --file backend/Dockerfile \
  backend/

# For Apple Silicon (linux/amd64 compatibility)
docker build \
  --tag legallens-backend:local \
  --platform linux/amd64 \
  --file backend/Dockerfile \
  backend/
```

### Expected Output

```
[+] Building 120.5s (15/15) FINISHED

 => [stage-1  1/8] FROM python:3.13-slim-bookworm
 => [stage-1  2/8] WORKDIR /app
 => [stage-1  3/8] RUN apt-get update && apt-get install -y --no-install-recommends ...
 => [stage-1  4/8] RUN pip install uv==0.4.0
 => [stage-1  5/8] COPY pyproject.toml uv.lock ./
 => [stage-1  6/8] RUN uv sync --frozen --no-dev
   => installing dependencies (this takes 30-60s)
 => [stage-1  7/8] COPY . .
 => [stage-2  1/7] FROM python:3.13-slim-bookworm
 => [stage-2  2/7] WORKDIR /app
 => [stage-2  3/7] RUN apt-get update && apt-get install -y --no-install-recommends ...
 => [stage-2  4/7] RUN useradd --create-home appuser
 => [stage-2  5/7] COPY --from=builder /app/.venv /app/.venv
 => [stage-2  6/7] COPY --from=builder /app /app
 => [stage-2  7/7] HEALTHCHECK
 => exporting to image

Successfully tagged legallens-backend:local
```

### Check Image Size

```bash
docker image ls legallens-backend:local
# Should show size ~200-250 MB
```

---

## 🚀 Run the Container

### Environment File (.env.docker)

Create `backend/.env.docker`:

```bash
# .env.docker - Backend environment (no secrets)

# API Configuration
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx  # Get from https://console.anthropic.com
DATABASE_URL=sqlite:///./data/test.db   # SQLite for dev
ENV=dev                                  # dev or production

# Optional settings
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
CORS_ORIGINS=http://localhost:3000,http://localhost:5173  # Frontend URLs
```

### Basic Run

```bash
# Run with port mapping and env file
docker run \
  --name legallens-backend \
  --publish 8000:8000 \
  --env-file backend/.env.docker \
  legallens-backend:local
```

### Run with Volume (Persistent Database)

```bash
# Create data directory for SQLite
mkdir -p ./backend/data

# Run with volume mount for persistent database
docker run \
  --name legallens-backend \
  --publish 8000:8000 \
  --volume ./backend/data:/app/data \
  --env-file backend/.env.docker \
  legallens-backend:local
```

### Run with Backend Networking

```bash
# If frontend is in Docker on same network
docker network create legallens-net

docker run \
  --name legallens-backend \
  --publish 8000:8000 \
  --network legallens-net \
  --volume ./backend/data:/app/data \
  --env-file backend/.env.docker \
  legallens-backend:local
```

### Run Interactive (with Shell)

```bash
# Start container and keep running
docker run -it \
  --name legallens-backend \
  --publish 8000:8000 \
  --env-file backend/.env.docker \
  legallens-backend:local

# In another terminal, open shell inside container
docker exec -it legallens-backend /bin/bash
```

---

## ✅ Verify It Works

### 1. Health Check

```bash
# Should return 200 OK
curl -I http://localhost:8000/api/docs

# Expected:
# HTTP/1.1 200 OK
# Content-Type: text/html; charset=utf-8
# Server: Uvicorn
```

### 2. Interactive API Docs

```bash
# Open in browser
open http://localhost:8000/api/docs

# Should show Swagger UI with all endpoints:
# - POST /api/ask
# - POST /api/summarize
# - POST /api/draft
# - etc.
```

### 3. Test Ask Endpoint

```bash
# Real API call
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the parties?",
    "chat_history": []
  }'

# Expected:
# {"success": true, "data": {"original_question": "...", ...}}
```

### 4. Check Container Health

```bash
# View health status
docker inspect legallens-backend | grep -A 10 "Health"

# Expected:
# "Health": {
#   "Status": "healthy",
#   "FailingStreak": 0,
#   ...
# }
```

### 5. View Logs

```bash
# Should show startup logs
docker logs legallens-backend

# Expected:
# Legal Lens API ready (env=dev, data=/app/data)
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

---

## 📝 View Logs

### Docker Logs

```bash
# All logs from start
docker logs legallens-backend

# Follow logs (like tail -f)
docker logs -f legallens-backend

# Last 100 lines
docker logs --tail 100 legallens-backend

# With timestamps
docker logs -t legallens-backend
```

### Typical Logs

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete
INFO:     127.0.0.1:12345 - "POST /api/ask HTTP/1.1" 200
INFO:     127.0.0.1:12346 - "GET /api/docs HTTP/1.1" 200
```

---

## 🐚 Access Container Shell

### Interactive Shell

```bash
# Open /bin/bash inside running container
docker exec -it legallens-backend /bin/bash

# Once inside:
ls /app/                    # See app files
python -c "import app"      # Test Python imports
cat /app/.env               # See environment (warning: may contain secrets)
```

### One-Time Commands

```bash
# Check Python version
docker exec legallens-backend python --version

# Check installed packages
docker exec legallens-backend pip list

# Test imports
docker exec legallens-backend python -c "from app.main import app; print('OK')"

# List files
docker exec legallens-backend ls -la /app/
```

---

## 🛑 Stop & Clean Up

### Stop Container

```bash
# Graceful shutdown (15 second timeout)
docker stop legallens-backend

# Forceful shutdown (immediate)
docker kill legallens-backend
```

### Remove Container & Image

```bash
# Remove stopped container
docker rm legallens-backend

# Remove image
docker rmi legallens-backend:local

# Remove all unused images/containers
docker system prune -a
```

---

## 🐞 Troubleshooting

### Problem: "Port 8000 already in use"

**Cause:** Another process using port 8000

**Fix:**
```bash
# Use different port
docker run -p 5000:8000 legallens-backend:local

# Or kill the process using port 8000
lsof -i :8000
kill -9 <PID>
```

### Problem: "ANTHROPIC_API_KEY not set" or invalid

**Cause:** Missing or wrong API key in .env.docker

**Fix:**
```bash
# Get key from https://console.anthropic.com
# Update .env.docker:
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Restart container
docker stop legallens-backend
docker run -p 8000:8000 --env-file backend/.env.docker legallens-backend:local
```

### Problem: Database errors / "Cannot open /app/data/test.db"

**Cause:** No persistent volume, database is lost on restart

**Fix:**
```bash
# Create data directory
mkdir -p ./backend/data

# Run with volume mount
docker run \
  --volume ./backend/data:/app/data \
  --env-file backend/.env.docker \
  legallens-backend:local

# Verify directory exists in container
docker exec legallens-backend ls -la /app/data/
```

### Problem: "Connection refused" from frontend

**Cause:** Frontend can't reach backend

**Fix:**
```bash
# If backend and frontend in Docker, use same network
docker network create legallens-net

# Run backend on network
docker run --network legallens-net --name backend legallens-backend:local

# Run frontend with backend URL
docker run --network legallens-net \
  -e VITE_API_BASE_URL=http://backend:8000/api \
  legallens-frontend:local
```

### Problem: "Module not found" errors

**Cause:** Dependency installation failed or packages missing

**Fix:**
```bash
# Rebuild without cache
docker build --tag legallens-backend:local --no-cache .

# Check uv.lock is present
ls -la backend/uv.lock

# Verify dependencies
docker exec legallens-backend pip list | grep langchain
```

### Problem: Slow startup (takes > 30 seconds)

**Cause:** App downloading models or initializing embeddings

**Expected behavior:**
```
First startup: 30-60s (downloads models)
Subsequent startups: 5-10s (models cached)
```

**Fix:**
- First startup is normal - models are cached in /app/data
- Subsequent starts will be faster
- For production, pre-warm the image by running once before deploying

---

## 🔄 Multi-Container Setup (Docker Compose)

### docker-compose.yml

```yaml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: legallens-backend
    ports:
      - "8000:8000"
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      DATABASE_URL: sqlite:///./data/test.db
      ENV: dev
      CORS_ORIGINS: http://localhost:3000,http://localhost:5173
    volumes:
      - ./backend/data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/docs"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
    networks:
      - legallens

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: legallens-frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_BASE_URL: http://backend:8000/api
      VITE_USE_MOCKS: "false"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - legallens

networks:
  legallens:
    driver: bridge
```

### .env.docker

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

### Run Both

```bash
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop both
docker-compose down
```

---

## 📊 Image Information

### Size Breakdown

```bash
docker history legallens-backend:local --human --no-trunc
```

### Typical Sizes

| Component | Size |
|-----------|------|
| python:3.13-slim-bookworm base | 150 MB |
| Python packages (langchain, fastapi, etc.) | 80-100 MB |
| Application code | 5-10 MB |
| **Total** | **200-250 MB** |

### Compare with Alternatives

| Approach | Size |
|----------|------|
| python:3.13 (full) | 1+ GB |
| python:3.13-slim | 150 MB + deps |
| Our multi-stage | 200-250 MB ⭐ |

---

## 🔧 Advanced Topics

### Running with GPU (If Needed Later)

```bash
# If using GPU for embeddings/models
docker run \
  --gpus all \
  --env-file backend/.env.docker \
  legallens-backend:local
```

### Environment Variables (Complete List)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
DATABASE_URL=sqlite:///./data/test.db
ENV=dev                              # or production
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR
CORS_ORIGINS=http://localhost:3000   # Comma-separated
PORT=8000                            # Override default port
WORKERS=1                            # Number of Uvicorn workers
```

### Production Deployment (Preview)

```bash
# Build for production
docker build \
  --tag legallens-backend:v1.0.0 \
  --build-arg ENV=production \
  .

# Tag for registry
docker tag legallens-backend:v1.0.0 myregistry.azurecr.io/legallens-backend:v1.0.0

# Push to Azure Container Registry
docker push myregistry.azurecr.io/legallens-backend:v1.0.0
```

---

## ✨ Summary

| Aspect | Value |
|--------|-------|
| Base Image | python:3.13-slim-bookworm |
| Final Size | ~200-250 MB |
| Build Time | ~2-3 minutes |
| Startup Time | 5-10 seconds (after model cache) |
| Port | 8000 |
| Non-root | Yes (appuser) |
| Health Check | HTTP GET /api/docs |
| Logs | stdout/stderr |
| SIGTERM | Handled by Uvicorn |

---

## 🚀 Quick Reference

```bash
# Build
docker build --tag legallens-backend:local backend/

# Run
docker run -p 8000:8000 --env-file backend/.env.docker legallens-backend:local

# Test
curl http://localhost:8000/api/docs

# Logs
docker logs -f legallens-backend

# Shell
docker exec -it legallens-backend /bin/bash

# Stop
docker stop legallens-backend

# Cleanup
docker rm legallens-backend
```

---

**Created:** 2026-10-28  
**Status:** Production-ready  
**Python Version:** 3.13  
**Package Manager:** uv (fast, reproducible)
