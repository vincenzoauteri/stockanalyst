# Multi-stage build for optimized production image
FROM node:lts-slim as builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies including Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    vim \
    build-essential \
    ca-certificates \
    sudo \
    gosu \
    python3 \
    python3-pip \
    python3-venv \
    lsb-release \
    shellcheck \
    gnupg && \
    curl -sL https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64 -o /usr/local/bin/hadolint && \
    chmod +x /usr/local/bin/hadolint && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
WORKDIR /tmp
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# --- Production stage ---
FROM node:lts-slim

# Re-install essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    shellcheck \
    git \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    python3-venv && \
    curl -sL https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64 -o /usr/local/bin/hadolint && \
    chmod +x /usr/local/bin/hadolint && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && \
    apt-get install -y gh && \
    rm -rf /var/lib/apt/lists/*

# Install Claude and Gemini CLI tools in the final image
RUN npm install -g @anthropic-ai/claude-code && \
    npm install -g @google/gemini-cli

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# Create non-root user for security
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} stockanalyst && \
    useradd --uid ${USER_UID} --gid ${USER_GID} --shell /bin/bash --create-home stockanalyst

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=stockanalyst:stockanalyst . .

# Create necessary directories
RUN mkdir -p /app/data && \
    chown -R stockanalyst:stockanalyst /app

# Switch to non-root user
USER stockanalyst

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Default command
CMD ["./startup.sh"]
