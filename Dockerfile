# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.11-slim AS builder

# Set python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install heavy system-level C++ compilers and utilities needed to build Pandas, SDV, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    graphviz \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create formal python virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the dependency tracker and install
COPY requirements.txt .

# Install dependencies into the /opt/venv directory
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ==========================================
# STAGE 2: FRONTEND BUILDER
# ==========================================
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ==========================================
# STAGE 3: RUNNER (Production Image)
# ==========================================
FROM python:3.11-slim AS runner

# Set python environment variables securely
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install only minimalistic runtime dependencies (graphviz required for anonymeter rendering if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user matching Kubernetes SecurityContext UID 1000
RUN useradd -m -u 1000 adracauser

# Set working directory
WORKDIR /app

# Copy the fully compiled virtual environment FROM the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the completely stateless built React SPA natively into production
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy the internal source code and structural directories
COPY src/ /app/src/
COPY data/ /app/data/
COPY logs/ /app/logs/
COPY reports/ /app/reports/

# Create necessary architectural directories for runtime and fix permission ownership for the secure user
RUN mkdir -p /app/data/input /app/data/output /app/models /app/logs && \
    chown -R adracauser:adracauser /app

# Switch away from root immediately
USER 1000

# Declare internal exposed port
EXPOSE 8501

# Execute Uvicorn Server directly natively
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8501"]
