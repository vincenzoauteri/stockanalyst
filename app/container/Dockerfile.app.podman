# Base builder stage
FROM python:3.12-slim AS builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
WORKDIR /tmp
COPY requirements.pinned.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Common production base stage
FROM python:3.12-slim AS base
# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user for security
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} ops \
    && useradd --uid ${USER_UID} --gid ${USER_GID} --shell /bin/bash --create-home ops

# Copy virtual environment from builder stage
COPY --from=builder --chown=ops:ops /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=ops:ops app/ .

# Create necessary directories with correct ownership
RUN mkdir -p /app/data /app/logs \
    && chown -R ops:ops /app/data /app/logs

# Switch to non-root user
USER ops

# Declare volumes
VOLUME ["/app/data", "/app/logs"]

# Webapp stage
FROM base AS webapp
# Set environment variables for production
ENV FLASK_APP=app.py \
    FLASK_ENV=production

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Default command - start webapp only
CMD ["python", "webapp_launcher.py", "--mode", "production"]

# Scheduler stage
FROM base AS scheduler
# Health check - verify scheduler is running
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import scheduler; print('Scheduler running')" || exit 1

# Default command - run scheduler in foreground
CMD ["python", "scheduler.py", "run-internal"]
