#!/bin/bash
# Stock Analyst Docker Build Script

set -e

echo "🐳 Building Stock Analyst Docker Image..."

# Get version from git or use default
VERSION=${VERSION:-$(git rev-parse --short HEAD 2>/dev/null || echo "latest")}
IMAGE_NAME="stockanalyst"
FULL_IMAGE_NAME="${IMAGE_NAME}:${VERSION}"

echo "📦 Building image: ${FULL_IMAGE_NAME}"

# Build the Docker image
docker build \
    --tag "${FULL_IMAGE_NAME}" \
    --tag "${IMAGE_NAME}:latest" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --build-arg VERSION="${VERSION}" \
    .

echo "✅ Successfully built ${FULL_IMAGE_NAME}"

# Show image info
echo "📊 Image details:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo "🚀 Ready to deploy! Use:"
echo "   docker run -p 5000:5000 ${FULL_IMAGE_NAME}"
echo "   or"
echo "   docker-compose up"