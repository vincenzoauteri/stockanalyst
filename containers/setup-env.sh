#!/bin/bash

# Script to extract current user's UID and GID and update .env file

# Get current user's UID, GID, and Docker GID
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)
DOCKER_GID=$(getent group docker | cut -d: -f3)

# Path to .env file
ENV_FILE=".env"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env file..."
    cat > "$ENV_FILE" << EOF
# Docker container user permissions
HOST_UID=$CURRENT_UID
HOST_GID=$CURRENT_GID
DOCKER_GID=$DOCKER_GID

# API Keys
GEMINI_API_KEY=
EOF
else
    echo "Updating .env file..."
    # Update HOST_UID
    if grep -q "^HOST_UID=" "$ENV_FILE"; then
        sed -i "s/^HOST_UID=.*/HOST_UID=$CURRENT_UID/" "$ENV_FILE"
    else
        echo "HOST_UID=$CURRENT_UID" >> "$ENV_FILE"
    fi
    
    # Update HOST_GID
    if grep -q "^HOST_GID=" "$ENV_FILE"; then
        sed -i "s/^HOST_GID=.*/HOST_GID=$CURRENT_GID/" "$ENV_FILE"
    else
        echo "HOST_GID=$CURRENT_GID" >> "$ENV_FILE"
    fi

    # Update DOCKER_GID
    if grep -q "^DOCKER_GID=" "$ENV_FILE"; then
        sed -i "s/^DOCKER_GID=.*/DOCKER_GID=$DOCKER_GID/" "$ENV_FILE"
    else
        echo "DOCKER_GID=$DOCKER_GID" >> "$ENV_FILE"
    fi
    
    # Add GEMINI_API_KEY if it doesn't exist
    if ! grep -q "^GEMINI_API_KEY=" "$ENV_FILE"; then
        echo "GEMINI_API_KEY=" >> "$ENV_FILE"
    fi
fi

echo "Updated .env file with:"
echo "HOST_UID=$CURRENT_UID"
echo "HOST_GID=$CURRENT_GID"
echo "DOCKER_GID=$DOCKER_GID"
echo ""
echo "Please set your GEMINI_API_KEY in the .env file before running docker-compose."
echo "Current .env file contents:"
cat "$ENV_FILE"
