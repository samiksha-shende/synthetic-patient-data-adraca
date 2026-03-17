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
# STAGE 2: RUNNER (Production Image)
# ==========================================
FROM python:3.11-slim AS runner

# Set python environment variables securely
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install only minimalistic runtime dependencies (graphviz required for anonymeter rendering if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for execution security
RUN useradd -m -r adraca_user

# Set working directory
WORKDIR /app

# Copy the fully compiled virtual environment FROM the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the internal source code
COPY src/ /app/src/

# Create necessary architectural directories for runtime
RUN mkdir -p /app/data/input /app/data/output /app/reports /app/models /app/logs

# Fix permission ownership for the secure user
RUN chown -R adraca_user:adraca_user /app

# 6. Copy ONLY the explicitly required source code modules logic and data directories
COPY src/ src/
COPY data/ data/
COPY logs/ logs/
COPY reports/ reports/
COPY .reports/ /app/reports

# 7. Add Enterprise Security Hardening (Non-Root User)
# Create an explicit unprivileged user matching Kubernetes SecurityContext UID 1000
RUN useradd -m -u 1000 adracauser && \
    chown -R adracauser:adracauser /app

# Switch away from root immediately
USER 1000

# 8. Declare internal exposed port
EXPOSE 8501

# 9. Execute Streamlit directly natively
CMD ["streamlit", "run", "src/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
