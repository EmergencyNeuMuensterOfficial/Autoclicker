#!/bin/bash

echo "========================================"
echo "  Autoclicker Ultimate - Setup"
echo "========================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed!"
    echo "Please install Python 3.6 or later."
    exit 1
fi

# Check tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "tkinter is not installed!"
    echo "On Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "On Fedora: sudo dnf install python3-tkinter"
    echo "On Mac: Install Python from python.org"
    exit 1
fi

echo "Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Failed to install dependencies!"
    exit 1
fi

echo "Starting bootstrapper..."
python3 bootstrapper.py