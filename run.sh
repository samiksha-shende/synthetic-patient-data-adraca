#!/bin/bash

# Adraca Synthetic Patient Engine
# Zero-Trust Offline Deployment Script

set -e

echo "=========================================="
echo "🧬 Starting Adraca Synthetic Patient Engine"
echo "=========================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "[!] Error: python3 could not be found. Please install Python 3.12+."
    exit 1
fi

ENV_DIR="adraca_env"

# Create a fresh virtual environment if one does not exist
if [ ! -d "$ENV_DIR" ]; then
    echo "[*] Creating isolated virtual environment: $ENV_DIR..."
    python3 -m venv $ENV_DIR
fi

echo "[*] Activating virtual environment..."
source $ENV_DIR/bin/activate

echo "[*] Installing dependencies securely from local ./wheels..."
pip install --no-index --find-links=./wheels -r requirements.txt

echo "[*] Booting Streamlit control panel on Port 8501..."
echo "[*] Press CTRL+C to stop the engine."

# Launch the frontend
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
