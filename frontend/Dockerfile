# Multi-stage build for LegalLens Frontend
# Stage 1: Build React app with TypeScript checking and Vite bundling
# Stage 2: Serve static files with nginx (lightweight, purpose-built for serving static content)

# === STAGE 1: BUILDER ===
# Using Node 22 Alpine for small footprint but full npm capability
FROM node:22-alpine AS builder

LABEL maintainer="LegalLens Team"
LABEL stage=builder

WORKDIR /app

# Copy dependency files first for Docker layer caching
# If package.json/package-lock.json don't change, this layer is reused
COPY package*.json ./

# Install dependencies with npm ci (clean install, respects lock file, faster than npm install)
# Using npm ci ensures reproducible builds from package-lock.json
RUN npm ci

# Copy source code after dependencies are installed
# This way, code changes don't invalidate the dependency layer
COPY . .

# Vite inlines VITE_* values at build time. .env is excluded from the build context,
# so the real-backend defaults are set here (override with --build-arg).
ARG VITE_USE_MOCKS=false
ARG VITE_API_BASE_URL=
ENV VITE_USE_MOCKS=$VITE_USE_MOCKS \
    VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build the React app with TypeScript checking and Vite bundling
# Output goes to dist/ folder (standard Vite output directory)
# tsc -b checks TypeScript types
# vite build bundles everything into optimized static assets
RUN npm run build

# Verify build succeeded by checking dist exists
RUN test -d dist || (echo "Build failed: dist directory not found" && exit 1)


# === STAGE 2: RUNTIME ===
# Using nginx:stable-alpine for serving static files
# Alpine is ~5MB, nginx adds ~10MB, final image ~15MB (vs 300MB+ with Node.js)
# nginx is purpose-built for serving static content with excellent performance
FROM nginx:stable-alpine

LABEL maintainer="LegalLens Team"
LABEL stage=runtime

# nginx runs as non-root user 'nginx' by default (security best practice)
# Verification: RUN id nginx

# Copy custom nginx configuration for SPA routing
# This config serves static files from /usr/share/nginx/html
# and routes all non-file requests to index.html (required for React Router)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built React app from builder stage to nginx html directory
# nginx serves files from /usr/share/nginx/html by default
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Create directory for runtime logs (nginx logs to stdout/stderr in container)
RUN mkdir -p /var/log/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d

# Expose port 3000 (matching development server port for consistency)
# nginx listens on 3000 inside container (see nginx.conf)
EXPOSE 3000

# Healthcheck: HTTP GET to / should return 200
# Used by Docker, Kubernetes (liveness/readiness probes), and orchestrators
# Interval 30s, timeout 3s, start period 5s, retries 3
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run nginx in foreground mode
# Required in containers: if nginx daemonizes, container exits
# -g "daemon off;" tells nginx to not fork into background
CMD ["nginx", "-g", "daemon off;"]
