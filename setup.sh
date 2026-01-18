#!/bin/bash

echo "========================================"
echo "  Autoclicker Ultimate - Portable Setup"
echo "========================================"
echo
echo "This installer will create a portable installation"
echo "in the current folder. No admin rights needed!"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed!"
    echo
    echo "Please install Python 3.6 or later."
    echo "Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "Fedora: sudo dnf install python3 python3-pip"
    echo "Mac: brew install python3"
    exit 1
fi

# Check tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠ tkinter is not installed!"
    echo
    echo "This is required for the GUI installer."
    echo "On Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "On Fedora: sudo dnf install python3-tkinter"
    echo "On Mac: Reinstall Python from python.org"
    echo
    echo "You can still use command-line mode."
    echo
    read -p "Continue without GUI? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Python found"
echo

# Run the installer
echo "Starting installer..."
python3 bootstrapper.py "$@"