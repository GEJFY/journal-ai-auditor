# JAIA Frontend Dockerfile
# Multi-stage build: Node.js build → Nginx serve
# Build context: project root (set via docker-compose)

# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files for layer caching
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy frontend source code
COPY frontend/ .

# Build-time API base URL (relative for Nginx proxy)
ARG VITE_API_BASE=/api/v1
ENV VITE_API_BASE=${VITE_API_BASE}

# Build the React app (renderer only, no Electron)
RUN npm run build:vite

# Stage 2: Production
FROM nginx:alpine AS production

# Copy built assets from build stage
COPY --from=build /app/dist/renderer /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
