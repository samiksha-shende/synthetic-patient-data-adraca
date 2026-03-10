#!/bin/bash

# Adraca Synthetic Patient Engine - Deployment Script
set -e

echo "=========================================="
echo "🚀 Deploying Adraca Synthetic Engine"
echo "=========================================="

# Check if data/input directory is empty
if [ ! -d "data/input" ] || [ -z "$(ls -A data/input)" ]; then
    echo "[WARNING] The data/input/ directory is empty or does not exist."
    echo "          The application may work, but no real data is available for ingestion."
else
    echo "[OK] Found data files in data/input/."
fi

# Build the Docker image
echo "Building the Docker image..."
docker-compose build

# Start the container in detached mode
echo "Starting the container in detached mode..."
docker-compose up -d

echo "=========================================="
echo "✅ Deployment Successful!"
echo "📡 Access the dashboard locally at: http://localhost:8501"
echo "=========================================="
