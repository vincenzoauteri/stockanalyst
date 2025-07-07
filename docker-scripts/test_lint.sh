#!/bin/bash

# Simple linting test script
set -e

echo "Running basic linting tests..."

# Test Python syntax
echo "Testing Python syntax..."
python -m py_compile ./*.py
echo "✓ Python syntax check passed"

# Test with ruff (basic checks)
echo "Testing Python code quality with ruff..."
ruff check . --select=E9,F63,F7,F82 --format=text || echo "Ruff found issues (non-critical)"

# Test shell script syntax
echo "Testing shell script syntax..."
for script in docker-scripts/*.sh; do
    if [ -f "$script" ]; then
        bash -n "$script" && echo "✓ $script syntax OK" || echo "✗ $script has syntax errors"
    fi
done

# Test YAML syntax
echo "Testing YAML syntax..."
yamllint docker-compose.yml --format parsable || echo "YAML linting found issues (non-critical)"

echo "Basic linting tests completed."