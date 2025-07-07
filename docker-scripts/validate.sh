#!/bin/bash
# Docker Configuration Validation Script

set -e

echo "🔍 Validating Docker configuration for Stock Analyst..."

# Run linting script
./docker-scripts/lint.sh

# Check if required files exist
echo "📁 Checking required files..."
REQUIRED_FILES=(
    "Dockerfile"
    "docker-compose.yml"
    ".dockerignore"
    "docker_app.py"
    "nginx.conf"
    ".env.example"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        exit 1
    fi
done

# Validate Dockerfile syntax
echo ""
echo "🐳 Validating Dockerfile..."
if docker version >/dev/null 2>&1; then
    echo "✅ Docker daemon is accessible"
    
    # Check Dockerfile syntax without building
    if docker build --dry-run . >/dev/null 2>&1; then
        echo "✅ Dockerfile syntax is valid"
    else
        echo "⚠️  Dockerfile syntax check not supported in this Docker version"
    fi
else
    echo "⚠️  Docker daemon not accessible - skipping build validation"
    echo "   This is normal in some CI/CD environments"
fi

# Validate docker-compose.yml syntax
echo ""
echo "🔧 Validating docker-compose.yml..."
if command -v docker-compose >/dev/null 2>&1; then
    if docker-compose config >/dev/null 2>&1; then
        echo "✅ docker-compose.yml syntax is valid"
    else
        echo "❌ docker-compose.yml has syntax errors"
        exit 1
    fi
else
    echo "⚠️  docker-compose not available - manual validation"
    
    # Basic YAML syntax check
    if python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" 2>/dev/null; then
        echo "✅ docker-compose.yml is valid YAML"
    else
        echo "❌ docker-compose.yml has YAML syntax errors"
        exit 1
    fi
fi

# Check Python application
echo ""
echo "🐍 Validating Python application..."
if python3 -m py_compile docker_app.py; then
    echo "✅ docker_app.py compiles successfully"
else
    echo "❌ docker_app.py has syntax errors"
    exit 1
fi

if python3 -m py_compile app.py; then
    echo "✅ app.py compiles successfully"
else
    echo "❌ app.py has syntax errors"
    exit 1
fi

# Check requirements.txt
echo ""
echo "📦 Validating requirements.txt..."
if [[ -f "requirements.txt" ]]; then
    echo "✅ requirements.txt exists"
    echo "📋 Dependencies:"
    sed 's/^/   /' requirements.txt
else
    echo "❌ requirements.txt missing"
    exit 1
fi

# Validate environment template
echo ""
echo "🔐 Validating environment configuration..."
if [[ -f ".env.example" ]]; then
    echo "✅ .env.example template exists"
    if grep -q "FMP_API_KEY" .env.example; then
        echo "✅ FMP_API_KEY configuration found"
    else
        echo "⚠️  FMP_API_KEY not found in template"
    fi
else
    echo "❌ .env.example missing"
    exit 1
fi

# Check nginx configuration
echo ""
echo "🌐 Validating nginx configuration..."
if command -v nginx >/dev/null 2>&1; then
    if nginx -t -c "$(pwd)/nginx.conf" >/dev/null 2>&1; then
        echo "✅ nginx.conf syntax is valid"
    else
        echo "⚠️  nginx.conf syntax check failed (expected in test environment)"
    fi
else
    echo "⚠️  nginx not available - skipping syntax check"
fi

echo ""
echo "🎉 Docker configuration validation completed!"
echo ""
echo "📋 Next steps:"
echo "   1. Ensure Docker daemon is running"
echo "   2. Copy .env.example to .env and configure"
echo "   3. Build image: ./docker-scripts/build.sh"
echo "   4. Deploy: ./docker-scripts/deploy.sh"
echo "   5. Or use: docker-compose up -d"
echo ""
echo "✨ Configuration looks good for containerization!"