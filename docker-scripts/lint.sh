#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Running linters..."

# Lint Python files
echo "Linting Python files..."
docker compose exec stockanalyst /opt/venv/bin/ruff check .

# Lint Shell scripts
echo "Linting Shell scripts..."
docker compose exec stockanalyst shellcheck docker-scripts/*.sh

# Lint Dockerfile
echo "Linting Dockerfile..."
docker compose exec stockanalyst hadolint Dockerfile

# Lint YAML files
echo "Linting YAML files..."
docker compose exec stockanalyst /opt/venv/bin/yamllint docker-compose.yml

# Lint Markdown files (disabled - markdownlint removed)
echo "Skipping Markdown linting..."

echo "Linting complete."
