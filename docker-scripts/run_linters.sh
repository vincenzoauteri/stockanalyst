#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Installing linters..."

pip install ruff yamllint

echo "Running linters..."

# Lint Python files
echo "Linting Python files..."
ruff check .

# Lint Shell scripts
echo "Linting Shell scripts..."
shellcheck docker-scripts/*.sh

# Lint Dockerfile
echo "Linting Dockerfile..."
hadolint Dockerfile

# Lint YAML files
echo "Linting YAML files..."
yamllint docker-compose.yml

# Lint Markdown files (disabled - markdownlint removed)
echo "Skipping Markdown linting..."

echo "Linting complete."
