## LegalLens Frontend - Docker Guide

**Production-ready Docker setup for React + TypeScript + Vite SPA**

---

## 📋 Overview

- **Base Image (Builder):** `node:22-alpine` — Full Node.js for building
- **Base Image (Runtime):** `nginx:stable-alpine` — Lightweight web server
- **Final Image Size:** ~15-20 MB (vs 300+ MB with Node.js)
- **Port:** 3000 (matches dev environment)
- **Runs As:** Non-root user (nginx)
- **Health Check:** HTTP GET to `/` endpoint

---

## 🏗️ Architecture Decisions

### Multi-Stage Build (Why?)

```
Stage 1: node:22-alpine
  ├─ npm ci (install dependencies)
  ├─ npm run build (compile TypeScript, bundle with Vite)
  └─ Outputs: dist/ folder

Stage 2: nginx:stable-alpine
  ├─ Copies dist/ from Stage 1
  ├─ Serves with custom nginx.conf
  └─ Final size: ~15-20 MB
```

**Why two stages?**
- Builder stage needs Node.js (300+ MB)
- Runtime only needs nginx to serve static files (15 MB)
- Reduces final image by 95% without sacrificing build capability
- Faster deploys, less bandwidth

### nginx vs Node.js for Runtime (Why?)

| Aspect | nginx | Node.js |
|--------|-------|---------|
| Size | 10 MB | 150+ MB |
| Startup | <1s | 2-3s |
| Memory | 5-10 MB | 100+ MB |
| Performance | Excellent | Good |
| SPA Routing | Via nginx.conf | Via server.js |
| Purpose | Built for serving static | General-purpose runtime |

**Verdict:** nginx is purpose-built, lightweight, and fast for serving static SPAs.

### SPA Routing (How?)

React Router needs all non-file requests to return `index.html`:

```
GET /                → index.html (React Router handles)
GET /documents/123   → index.html (React Router handles)
GET /api/ask         → Backend proxy (nginx.conf)
GET /js/main.abc.js  → main.abc.js (static file)
```

This is handled by nginx.conf:
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

---

## 🔨 Build the Image

### Command

```bash
# Build with tag legallens-frontend:local
docker build \
  --tag legallens-frontend:local \
  --file Dockerfile \
  .

# For Apple Silicon (linux/amd64 compatibility)
docker build \
  --tag legallens-frontend:local \
  --platform linux/amd64 \
  --file Dockerfile \
  .
```

### Expected Output

```
[+] Building 45.3s (11/11) FINISHED

 => [stage-1  1/6] FROM node:22-alpine
 => [stage-1  2/6] WORKDIR /app
 => [stage-1  3/6] COPY package*.json ./
 => [stage-1  4/6] RUN npm ci
 => [stage-1  5/6] COPY . .
 => [stage-1  6/6] RUN npm run build
 => [stage-2  1/4] FROM nginx:stable-alpine
 => [stage-2  2/4] COPY nginx.conf /etc/nginx/conf.d/default.conf
 => [stage-2  3/4] COPY --from=builder /app/dist /usr/share/nginx/html
 => [stage-2  4/4] HEALTHCHECK
 => exporting to image
 => => naming to docker.io/library/legallens-frontend:local

Successfully tagged legallens-frontend:local
```

### Check Image Size

```bash
docker image ls legallens-frontend:local
# Should show size ~15-20 MB
```

---

## 🚀 Run the Container

### Environment File (.env.docker)

Create `frontend/.env.docker`:

```bash
# .env.docker - Frontend environment (no secrets, safe to commit)

# Backend API URL
# For local testing: http://localhost:5000
# For container networking: http://backend:8000
# For production: https://api.yourdomain.com
VITE_API_BASE_URL=http://localhost:5000/api

# Use mock API (true for testing without backend, false for real backend)
VITE_USE_MOCKS=false
```

**⚠️ Important:** These are build-time variables (baked into dist/ during build). They cannot be changed at runtime. If you need runtime configuration, you'll need a different approach (see "Runtime Configuration" section below).

### Basic Run

```bash
# Run with port mapping
docker run \
  --name legallens-frontend \
  --publish 3000:3000 \
  --env-file frontend/.env.docker \
  legallens-frontend:local
```

### Run with Backend Networking

```bash
# If backend is in a Docker network
docker run \
  --name legallens-frontend \
  --publish 3000:3000 \
  --network legallens-network \
  --env VITE_API_BASE_URL=http://backend:8000/api \
  legallens-frontend:local
```

### Run with Interactive Shell

```bash
# Start container and keep it running
docker run -it \
  --name legallens-frontend \
  --publish 3000:3000 \
  --env-file frontend/.env.docker \
  legallens-frontend:local

# In another terminal, open shell inside container
docker exec -it legallens-frontend /bin/sh
```

---

## ✅ Verify It Works

### 1. Health Check

```bash
# Should return 200 OK
curl -I http://localhost:3000/

# Expected:
# HTTP/1.1 200 OK
# Content-Type: text/html
# Content-Length: 1234
```

### 2. Load Homepage

```bash
# Open in browser
open http://localhost:3000

# Or curl
curl http://localhost:3000 | head -20
```

### 3. Test SPA Routing

```bash
# These should all return index.html (React handles routing)
curl http://localhost:3000/
curl http://localhost:3000/library
curl http://localhost:3000/settings
curl http://localhost:3000/c/abc123

# Compare with actual files (should 404)
curl -I http://localhost:3000/nonexistent.js
# HTTP/1.1 200 OK (actually serving index.html, which is correct)
```

### 4. Test Backend Proxy

```bash
# If backend is running on localhost:5000
curl -X POST http://localhost:3000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"test","chat_history":[]}'

# Should forward to backend and return response
```

### 5. Check Docker Health

```bash
# See container status
docker ps -a | grep legallens-frontend

# Check health status
docker inspect legallens-frontend | grep -A 5 "Health"

# Expected:
# "Health": {
#   "Status": "healthy",
#   ...
# }
```

---

## 📝 View Logs

### Docker Logs

```bash
# All logs from start
docker logs legallens-frontend

# Follow logs (like tail -f)
docker logs -f legallens-frontend

# Last 50 lines
docker logs --tail 50 legallens-frontend

# With timestamps
docker logs -t legallens-frontend
```

### Typical Logs

```
nginx: the configuration file /etc/nginx/conf.d/default.conf syntax is ok
nginx: configuration file /etc/nginx/conf.d/default.conf test is successful
```

---

## 🐚 Access Container Shell

### Interactive Shell

```bash
# Open /bin/sh inside running container
docker exec -it legallens-frontend /bin/sh

# Once inside:
ls /usr/share/nginx/html/    # See built files
cat /etc/nginx/conf.d/default.conf  # See nginx config
```

### One-Time Commands

```bash
# Check nginx version
docker exec legallens-frontend nginx -v

# Test nginx config
docker exec legallens-frontend nginx -t

# List files in nginx root
docker exec legallens-frontend ls -la /usr/share/nginx/html/
```

---

## 🛑 Stop & Clean Up

### Stop Container

```bash
# Graceful shutdown (15 second timeout)
docker stop legallens-frontend

# Forceful shutdown (immediate)
docker kill legallens-frontend
```

### Remove Container

```bash
# Remove stopped container
docker rm legallens-frontend

# Remove image
docker rmi legallens-frontend:local

# Remove all related images and containers
docker system prune -a
```

---

## 🐞 Troubleshooting

### Problem: "Connection refused" when calling /api

**Cause:** Backend not running or not accessible

**Fix:**
```bash
# Check if backend is running
curl http://localhost:5000/api/docs

# If running on different host, update .env.docker
VITE_API_BASE_URL=http://<backend-host>:5000/api

# Rebuild image
docker build --tag legallens-frontend:local .

# Run again
docker run --env-file .env.docker legallens-frontend:local
```

### Problem: "Bad gateway" errors in browser

**Cause:** nginx can't reach backend

**Fix:**
```bash
# Check nginx logs
docker logs legallens-frontend

# Test backend from inside container
docker exec legallens-frontend curl http://backend:8000/api/docs

# If container can't resolve 'backend', run with network
docker run --network legallens-network legallens-frontend:local
```

### Problem: "Port already in use"

**Cause:** Port 3000 is taken by another process

**Fix:**
```bash
# Use different port
docker run -p 8080:3000 legallens-frontend:local

# Then access at http://localhost:8080

# Or kill the process using port 3000
lsof -i :3000  # Find process
kill -9 <PID>  # Kill it
```

### Problem: "Failed to load module" errors in browser console

**Cause:** Built files don't match browser expectations (rare with Vite)

**Fix:**
```bash
# Rebuild from scratch
docker system prune -a  # Remove all images
docker build --tag legallens-frontend:local --no-cache .

# Run again
docker run --publish 3000:3000 legallens-frontend:local
```

---

## 🔄 Multi-Container Setup

### docker-compose.yml

```yaml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5000:8000"
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      DATABASE_URL: sqlite:///./test.db
    networks:
      - legallens

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      VITE_API_BASE_URL: http://backend:8000/api
      VITE_USE_MOCKS: "false"
    depends_on:
      - backend
    networks:
      - legallens

networks:
  legallens:
    driver: bridge
```

### Run Both

```bash
# Start both services
docker-compose up -d

# View logs
docker-compose logs -f frontend

# Stop both
docker-compose down
```

---

## 🔧 Advanced Topics

### Runtime Configuration (If Needed Later)

Currently, environment variables are set at **build time** (baked into dist/). If you need **runtime configuration**:

**Option 1: nginx substitute**
```nginx
location /config.json {
    default_type application/json;
    return 200 '{"apiUrl":"${API_URL}"}';
}
```

**Option 2: Node.js wrapper**
```
Use a small Node.js server to serve files and inject env vars into index.html
```

For now, rebuild the image with new variables (recommended approach).

### Cross-Platform Builds

```bash
# Build for multiple platforms
docker buildx build \
  --tag legallens-frontend:latest \
  --platform linux/amd64,linux/arm64 \
  --push \
  .
```

### Image Optimization

Current Dockerfile already uses best practices:
- ✅ Multi-stage build
- ✅ Alpine base images
- ✅ Layer caching (dependencies before code)
- ✅ .dockerignore
- ✅ Non-root user
- ✅ Health checks

To reduce further:
- Minify nginx.conf (marginal gain)
- Remove comments (docker logs still have them)
- Use distroless image (loses shell access for debugging)

### Kubernetes Deployment (Preview)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: legallens-frontend
spec:
  containers:
  - name: frontend
    image: legallens-frontend:latest
    ports:
    - containerPort: 3000
    livenessProbe:
      httpGet:
        path: /
        port: 3000
      initialDelaySeconds: 10
      periodSeconds: 30
    readinessProbe:
      httpGet:
        path: /
        port: 3000
      initialDelaySeconds: 5
      periodSeconds: 10
```

---

## 📊 Image Information

### Size Breakdown

```bash
# Check image size
docker image inspect legallens-frontend:local --format='{{json .Size}}'
# Should be ~15-20 MB

# Layer breakdown
docker image history legallens-frontend:local
```

### Typical Sizes

| Layer | Size |
|-------|------|
| node:22-alpine (builder base) | 165 MB |
| After npm ci | 450 MB |
| After npm run build | 450 MB |
| nginx:stable-alpine (runtime base) | 10 MB |
| After copying dist/ | 15-20 MB |

**Final image: 15-20 MB** (95% smaller than Node.js approach)

---

## ✨ Summary

| Aspect | Value |
|--------|-------|
| Base Images | node:22-alpine, nginx:stable-alpine |
| Final Size | ~15-20 MB |
| Build Time | ~1-2 minutes |
| Startup Time | <1 second |
| Port | 3000 |
| Non-root | Yes (nginx user) |
| Health Check | HTTP GET / |
| Logs | stdout/stderr |
| SIGTERM | Handled by nginx |

---

## 🚀 Quick Reference

```bash
# Build
docker build --tag legallens-frontend:local .

# Run
docker run -p 3000:3000 --env-file .env.docker legallens-frontend:local

# Test
curl http://localhost:3000/

# Logs
docker logs -f <container-id>

# Shell
docker exec -it <container-id> /bin/sh

# Clean
docker stop <container-id> && docker rm <container-id>
```

---

**Created:** 2026-10-28  
**Status:** Production-ready  
**Tested:** ✅ Locally (build succeeds, image runs, health check passes)
