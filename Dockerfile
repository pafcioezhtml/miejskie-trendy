# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim
WORKDIR /app

# Install system deps for lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Railway sets PORT env var
ENV PORT=8000
ENV FRONTEND_DIST=/app/frontend/dist
EXPOSE ${PORT}

CMD ["python", "-m", "miejskie_trendy.api"]
