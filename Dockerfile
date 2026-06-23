# ==========================================
# Phase 1: Build Frontend (React + Vite)
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy package files
COPY demo_VietGuide_AI-main/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source code
COPY demo_VietGuide_AI-main/ ./

# Build production bundle
RUN npm run build

# ==========================================
# Phase 2: Build Backend & Serve App
# ==========================================
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and pre-built vector DB & location data
COPY src/ ./src/
COPY data/ ./data/
COPY qdrant_data/ ./qdrant_data/

# Copy built frontend assets from Phase 1 builder
COPY --from=frontend-builder /app/frontend/dist ./demo_VietGuide_AI-main/dist

# Expose backend port
EXPOSE 8000

# Set environment variables for execution
ENV HOST=0.0.0.0
ENV PORT=8000

# Execute server
CMD ["python", "-m", "src.api.main"]
