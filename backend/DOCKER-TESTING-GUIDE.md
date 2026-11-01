## Backend Docker Testing Guide

**Complete instructions for building, running, and verifying the LegalLens backend Docker image**

---

## ✅ What Was Created

### Files

1. **Dockerfile** — Multi-stage build
   - Stage 1: Python builder with uv + dependencies
   - Stage 2: Python slim runtime
   - Final image: ~200-250 MB

2. **.dockerignore** — Build context exclusions
   - Excludes .venv, tests, .env, __pycache__, etc.
   - Speeds up Docker build

3. **DOCKER.md** — Complete documentation
   - Architecture decisions explained
   - Multi-stage build rationale
   - All build and run commands
   - Environment variables
   - Troubleshooting guide

---

## 🔨 Build Instructions

### On Windows with Docker Desktop

```bash
cd backend

# Basic build
docker build --tag legallens-backend:local .

# For Apple Silicon (build for linux/amd64)
docker build --platform linux/amd64 --tag legallens-backend:local .
```

### Expected Output

```
[+] Building 120.5s (15/15) FINISHED

Step 1/15 : FROM python:3.13-slim-bookworm AS builder
Step 2/15 : LABEL maintainer="LegalLens Team"
Step 3/15 : WORKDIR /app
Step 4/15 : RUN apt-get update && apt-get install -y --no-install-recommends ...
Step 5/15 : RUN pip install uv==0.4.0
Step 6/15 : COPY pyproject.toml uv.lock ./
Step 7/15 : RUN uv sync --frozen --no-dev
 => [Installing packages...]
 => [langchain, anthropic, fastapi, uvicorn, chromadb, sentence-transformers, etc.]
Step 8/15 : COPY . .
Step 9/15 : FROM python:3.13-slim-bookworm
Step 10/15: WORKDIR /app
Step 11/15: RUN apt-get update && apt-get install -y --no-install-recommends ...
Step 12/15: RUN useradd --create-home --shell /bin/bash appuser
Step 13/15: COPY --from=builder /app/.venv /app/.venv
Step 14/15: COPY --from=builder /app /app
Step 15/15: HEALTHCHECK

Successfully tagged legallens-backend:local
```

### Verify Build Succeeded

```bash
# List images
docker image ls legallens-backend

# Should show:
# REPOSITORY              TAG     IMAGE ID      CREATED        SIZE
# legallens-backend       local   abc123def456  2 minutes ago   230MB

# Inspect image
docker image inspect legallens-backend:local | grep -A 2 '"Size"'
```

---

## 🚀 Run Instructions

### Create Environment File

**backend/.env.docker**

```bash
# Anthropic API Configuration
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Database Configuration
DATABASE_URL=sqlite:///./data/test.db

# Application Environment
ENV=dev

# Logging
LOG_LEVEL=INFO

# CORS (for frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Start Container (Foreground)

```bash
# Basic run - see logs in terminal
docker run \
  --name legallens-backend \
  --publish 8000:8000 \
  --env-file backend/.env.docker \
  legallens-backend:local
```

### Start Container (Background)

```bash
# Run in background (-d flag)
docker run -d \
  --name legallens-backend \
  --publish 8000:8000 \
  --env-file backend/.env.docker \
  legallens-backend:local

# View logs
docker logs -f legallens-backend

# Stop
docker stop legallens-backend
```

### Start with Persistent Database

```bash
# Create data directory
mkdir -p backend/data

# Run with volume mount (database persists across restarts)
docker run \
  --name legallens-backend \
  --publish 8000:8000 \
  --volume ./backend/data:/app/data \
  --env-file backend/.env.docker \
  legallens-backend:local
```

### Expected Startup Output

```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
2026-10-28T10:30:45.123456Z INFO  legallens [-] Legal Lens API ready (env=dev, data=/app/data)
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## ✅ Verification Tests

### Test 1: Health Check

```bash
# Should return 200 OK
curl -I http://localhost:8000/api/docs

# Expected:
# HTTP/1.1 200 OK
# Content-Type: text/html; charset=utf-8
# Server: Uvicorn
```

### Test 2: Interactive API Docs

```bash
# Open in browser
open http://localhost:8000/api/docs

# Should see:
# - Swagger UI
# - All endpoints listed (ask, summarize, draft, etc.)
# - "Try it out" buttons
```

### Test 3: Test Ask API

```bash
# Real API call - assumes documents are ingested
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the parties?",
    "chat_history": []
  }'

# Expected:
# {"success": true, "data": {"original_question": "What are the parties?", ...}}

# If no documents:
# {"success": false, "error": "No documents available", "code": "NO_DOCUMENTS"}
```

### Test 4: OpenAPI Schema

```bash
# Get OpenAPI specification
curl http://localhost:8000/api/openapi.json | jq '.paths | keys' | head -10

# Should show all API endpoints
```

### Test 5: Docker Health Check

```bash
# Check container health status
docker inspect --format='{{.State.Health.Status}}' legallens-backend
# Expected: healthy

# View health check details
docker inspect legallens-backend | jq '.[] | .State.Health'
```

### Test 6: Verify Non-Root User

```bash
# Check process runs as appuser, not root
docker exec legallens-backend ps aux | grep uvicorn

# Expected output shows:
# appuser  1 ... uvicorn app.main:app
# (NOT root)
```

### Test 7: Container Resources

```bash
# View memory usage
docker stats legallens-backend

# Expected:
# MEM USAGE / LIMIT
# 100-200MB / X GB (very lightweight)
```

### Test 8: Database Persistence

```bash
# Check database file exists
docker exec legallens-backend ls -la /app/data/

# Should show:
# test.db  (SQLite database file)

# Stop and restart container
docker stop legallens-backend
docker start legallens-backend

# Database should still exist (persisted to volume)
docker exec legallens-backend ls -la /app/data/
```

---

## 🔍 Debugging

### View Logs

```bash
# All logs
docker logs legallens-backend

# Follow logs (tail -f)
docker logs -f legallens-backend

# Last 100 lines
docker logs --tail 100 legallens-backend

# With timestamps
docker logs -t legallens-backend
```

### Access Shell

```bash
# Open shell inside running container
docker exec -it legallens-backend /bin/bash

# Once inside, you can:
ls /app/                    # View app files
python -c "import app"      # Test imports
cat /etc/passwd             # See appuser user exists
ps aux                       # See running processes
```

### Test Python Imports

```bash
# Verify all dependencies installed
docker exec legallens-backend python -c "
import langchain
import anthropic
import fastapi
import chromadb
import sentence_transformers
print('✅ All imports OK')
"
```

### Check Environment Variables

```bash
# View environment inside container
docker exec legallens-backend env | grep -E "ANTHROPIC|DATABASE|ENV"

# Should show:
# ANTHROPIC_API_KEY=sk-ant-...
# DATABASE_URL=sqlite:///./data/test.db
# ENV=dev
```

---

## 🐞 Troubleshooting

### Issue: "ANTHROPIC_API_KEY not set"

**Cause:** API key missing from .env.docker

**Fix:**
```bash
# Get key from https://console.anthropic.com

# Update .env.docker
echo "ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx" > backend/.env.docker

# Restart container
docker restart legallens-backend

# Verify
docker logs legallens-backend | grep -i "api ready"
```

### Issue: "Port 8000 already in use"

**Cause:** Another process using port 8000

**Fix:**
```bash
# Use different port
docker run -p 5000:8000 legallens-backend:local

# Then access at http://localhost:5000/api/docs

# Or kill process using port 8000
lsof -i :8000
kill -9 <PID>
```

### Issue: "Cannot open /app/data/test.db"

**Cause:** No persistent volume, database is lost on restart

**Fix:**
```bash
# Create data directory
mkdir -p backend/data

# Run with volume
docker run \
  --volume ./backend/data:/app/data \
  --env-file backend/.env.docker \
  legallens-backend:local

# Verify
docker exec legallens-backend ls -la /app/data/
```

### Issue: "Module not found" errors

**Cause:** Dependency installation failed

**Fix:**
```bash
# Rebuild from scratch (no cache)
docker build --tag legallens-backend:local --no-cache .

# Watch for errors during dependency installation

# Verify dependencies installed
docker exec legallens-backend pip list | grep langchain
```

### Issue: Health check keeps failing

**Cause:** App not starting properly

**Fix:**
```bash
# Check logs for errors
docker logs legallens-backend | tail -20

# Test API manually
curl http://localhost:8000/api/docs -v

# Check health status
docker inspect legallens-backend | jq '.[] | .State.Health'

# Increase start period if app needs more time (edit Dockerfile)
```

### Issue: Slow startup (takes > 30 seconds)

**Expected behavior:**
- First startup: 30-60s (downloads LLM models, embedding models)
- Subsequent startups: 5-10s (models cached in /app/data)

**Fix:**
```bash
# This is normal. First run:
docker run --volume ./backend/data:/app/data legallens-backend:local

# Let it run fully, models are cached
# Subsequent runs will be much faster
```

---

## 🔄 Multi-Container Setup (Docker Compose)

Create `docker-compose.yml` in project root:

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

**Run both:**
```bash
docker-compose up -d

# Logs
docker-compose logs -f backend

# Stop both
docker-compose down
```

---

## ✨ Quick Reference

```bash
# Build
docker build -t legallens-backend:local backend/

# Run (foreground)
docker run -p 8000:8000 --env-file backend/.env.docker legallens-backend:local

# Run (background)
docker run -d -p 8000:8000 --env-file backend/.env.docker legallens-backend:local

# Test API
curl http://localhost:8000/api/docs

# View logs
docker logs -f legallens-backend

# Shell
docker exec -it legallens-backend /bin/bash

# Stop
docker stop legallens-backend

# Cleanup
docker rm legallens-backend
```

---

## 📝 Testing Checklist

- [ ] Docker build succeeds without errors
- [ ] Image size is 200-250 MB
- [ ] Container starts without errors
- [ ] Health check reports "healthy"
- [ ] `curl http://localhost:8000/api/docs` returns 200 OK
- [ ] Swagger UI loads in browser at /api/docs
- [ ] Test API call succeeds
- [ ] Process runs as non-root user (appuser)
- [ ] Database file created in /app/data
- [ ] Logs show no errors
- [ ] Container stops gracefully with docker stop
- [ ] Memory usage is <200 MB at idle

---

## 🎉 Summary

**Backend Dockerfile created with:**

✅ Multi-stage build (Python builder → slim runtime)  
✅ Final image: ~200-250 MB  
✅ Production-ready Uvicorn ASGI server  
✅ Health check for orchestrators  
✅ Non-root user (appuser)  
✅ uv package manager (fast, reproducible)  
✅ Volume support for persistent database  
✅ Graceful shutdown on SIGTERM  
✅ Comprehensive documentation  
✅ Security best practices  

**Ready to build and deploy!** 🚀
