#!/bin/bash

echo "=========================================="
echo "ZeCo Setup Script (Linux)"
echo "=========================================="

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

echo "Installing dependencies..."
# Try to install cryptography. 
# Note: On some Linux distros, you might need 'python3-cryptography' via apt/dnf/pacman
# instead of pip if it's a system managed environment.
# We'll try pip first.
python3 -m pip install cryptography || echo "Warning: pip install failed. Ensure you have python3-pip or python3-cryptography installed."

echo ""
echo "Running setup script..."
python3 setup_env.py

echo ""
echo "Setup finished."
