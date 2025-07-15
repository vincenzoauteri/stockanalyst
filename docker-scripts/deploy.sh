#!/bin/bash
# Stock Analyst Docker Deployment Script

set -e

# Configuration
CONTAINER_NAME="stockanalyst-app"
IMAGE_NAME="stockanalyst:latest"
PORT=${PORT:-5000}
ENV_FILE=${ENV_FILE:-.env}

echo "🚀 Deploying Stock Analyst..."

# Stop existing container if running
if docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
    echo "🛑 Stopping existing container..."
    docker stop "${CONTAINER_NAME}"
    docker rm "${CONTAINER_NAME}"
fi

# Check if .env file exists
if [ ! -f "${ENV_FILE}" ]; then
    echo "⚠️  Environment file ${ENV_FILE} not found"
    echo "📝 Creating from template..."
    cp .env.example "${ENV_FILE}"
    echo "✏️  Please edit ${ENV_FILE} with your configuration"
    echo "❓ Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create data volume if it doesn't exist
docker volume create stockanalyst_data 2>/dev/null || true

echo "🐳 Starting container..."

# Run the container
docker run -d \
    --name "${CONTAINER_NAME}" \
    --env-file "${ENV_FILE}" \
    -p "${PORT}:5000" \
    -v stockanalyst_data:/app/data \
    --restart unless-stopped \
    "${IMAGE_NAME}"

echo "✅ Container started successfully!"

# Show container status
echo "📊 Container status:"
docker ps -f name="${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🌐 Application URLs:"
echo "   Web Interface: http://localhost:${PORT}"
echo "   API Endpoint:  http://localhost:${PORT}/api/stocks"
echo "   Health Check:  http://localhost:${PORT}/"

echo ""
echo "📋 Useful commands:"
echo "   View logs:     docker logs -f ${CONTAINER_NAME}"
echo "   Stop app:      docker stop ${CONTAINER_NAME}"
echo "   Restart app:   docker restart ${CONTAINER_NAME}"
echo "   Remove app:    docker rm -f ${CONTAINER_NAME}"