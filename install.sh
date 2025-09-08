#!/bin/bash
# Wallbox eM4 EVSE Controller - Dependency Installation Script (Linux/macOS)
#
# This script installs all required Python dependencies for the eM4 controller

set -e

echo "================================================"
echo "   Wallbox eM4 EVSE Controller Setup"
echo "================================================"
echo

echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.7+ using your package manager"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

python3 --version
echo

echo "Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo
echo "================================================"
echo "   Installation Complete!"
echo "================================================"
echo
echo "You can now run the eM4 controller:"
echo "  python3 em4_interface.py    (Interactive interface)"
echo "  python3 em4_modbus.py --help (Command line)"
echo
echo "Before first use, edit config.py to set your eM4 IP address."
echo