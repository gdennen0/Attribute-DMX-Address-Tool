"""
MVR File Analyzer - Main Application
A simple tool to analyze MVR files and extract fixture addresses.

Run this file directly to start the GUI application.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import main as gui_main


def main():
    """Start the MVR File Analyzer application."""
    print("Starting MVR File Analyzer...")
    
    # Start the GUI application
    gui_main()


if __name__ == "__main__":
    main() 